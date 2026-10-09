import logging
import uuid
from pathlib import Path
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (
    AppError,
    EmptyFileError,
    FileNotFoundInDbError,
    FileNotReadyError,
    FileTooLargeError,
    ProcessingError,
)
from app.models import FileStatus, GeospatialFile
from app.repositories.file_repository import FileRepository
from app.schemas.feature import (
    FeatureMeasurement,
    GeoJsonFeature,
    GeoJsonFeatureCollection,
    MeasurementsResponse,
)
from app.schemas.file import FileDetail, FileSummary, StatsResponse
from app.schemas.measurement import Measurement
from app.services.geospatial_service import ProcessedDataset, process_dataset
from app.utils.file_validation import detect_file_type, safe_filename

logger = logging.getLogger(__name__)

UPLOAD_CHUNK_BYTES = 1024 * 1024


class FileService:
    """Orchestrates upload -> validation -> processing -> persistence."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.repo = FileRepository(session)
        self.settings = settings

    # ---- upload / processing -------------------------------------------------

    def upload(self, filename: str, stream: BinaryIO) -> GeospatialFile:
        original_name = safe_filename(filename)
        file_type = detect_file_type(original_name)

        file_id = uuid.uuid4()
        stored_name = f"{file_id}{Path(original_name).suffix}"
        stored_path = self._store_upload(stream, stored_name)

        record = self.repo.add(
            GeospatialFile(
                id=file_id,
                original_filename=original_name,
                stored_filename=stored_name,
                file_type=file_type,
                file_size=stored_path.stat().st_size,
                status=FileStatus.PROCESSING,
            )
        )
        self._process(record, stored_path)
        return record

    def _store_upload(self, stream: BinaryIO, stored_name: str) -> Path:
        upload_dir = self.settings.upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / stored_name
        written = 0
        try:
            with destination.open("wb") as sink:
                while chunk := stream.read(UPLOAD_CHUNK_BYTES):
                    written += len(chunk)
                    if written > self.settings.max_upload_bytes:
                        raise FileTooLargeError(
                            f"The file exceeds the {self.settings.max_upload_mb} MB upload limit."
                        )
                    sink.write(chunk)
            if written == 0:
                raise EmptyFileError()
        except AppError:
            destination.unlink(missing_ok=True)
            raise
        return destination

    def _process(self, record: GeospatialFile, stored_path: Path) -> None:
        try:
            dataset = process_dataset(stored_path, record.file_type, self.settings)
            self._persist_success(record, dataset)
        except AppError as exc:
            self._persist_failure(record, stored_path, exc.message)
            exc.details["file_id"] = str(record.id)
            raise
        except Exception as exc:
            logger.exception("Unexpected failure processing file %s", record.id)
            self.repo.session.rollback()
            error = ProcessingError(file_id=str(record.id))
            self._persist_failure(record, stored_path, error.message)
            raise error from exc

    def _persist_success(self, record: GeospatialFile, dataset: ProcessedDataset) -> None:
        self.repo.add_features(
            record.id,
            [
                {
                    "feature_index": f.feature_index,
                    "geometry_type": f.geometry_type,
                    "geometry": f.geometry,
                    "properties": f.properties,
                    "measurement_status": f.measurement.status.value,
                    "measurement_type": f.measurement.type,
                    "measurement_value": f.measurement.value,
                    "measurement_unit": f.measurement.unit,
                }
                for f in dataset.features
            ],
        )
        record.original_crs = dataset.original_crs
        record.projected_crs = dataset.projected_crs
        record.feature_count = len(dataset.features)
        record.status = FileStatus.COMPLETED
        self.repo.save(record)

    def _persist_failure(self, record: GeospatialFile, stored_path: Path, message: str) -> None:
        record.status = FileStatus.FAILED
        record.error_message = message
        self.repo.save(record)
        stored_path.unlink(missing_ok=True)

    # ---- queries -------------------------------------------------------------

    def get_file(self, file_id: uuid.UUID) -> GeospatialFile:
        record = self.repo.get(file_id)
        if record is None:
            raise FileNotFoundInDbError()
        return record

    def get_detail(self, file_id: uuid.UUID) -> FileDetail:
        record = self.get_file(file_id)
        detail = FileDetail.model_validate(record)
        detail.geometry_summary = self.repo.geometry_summaries([record.id]).get(record.id, {})
        return detail

    def list_files(self, limit: int, offset: int) -> list[FileSummary]:
        records = self.repo.list_recent(limit, offset)
        summaries = self.repo.geometry_summaries([r.id for r in records])
        result = []
        for record in records:
            item = FileSummary.model_validate(record)
            item.geometry_summary = summaries.get(record.id, {})
            result.append(item)
        return result

    def measurements(self, file_id: uuid.UUID) -> MeasurementsResponse:
        record = self._completed_file(file_id)
        features = [
            FeatureMeasurement(
                feature_index=f.feature_index,
                geometry_type=f.geometry_type,
                geometry=f.geometry,
                crs=record.original_crs,
                properties=f.properties,
                measurement=_measurement_of(f),
                measurement_status=f.measurement_status,
            )
            for f in self.repo.features_for(record.id)
        ]
        return MeasurementsResponse(
            file_id=record.id,
            original_crs=record.original_crs,
            projected_crs=record.projected_crs,
            feature_count=len(features),
            features=features,
        )

    def geojson(self, file_id: uuid.UUID) -> GeoJsonFeatureCollection:
        record = self._completed_file(file_id)
        return GeoJsonFeatureCollection(
            features=[
                GeoJsonFeature(
                    geometry=f.geometry,
                    properties={
                        "feature_index": f.feature_index,
                        "geometry_type": f.geometry_type,
                        "measurement": _measurement_of(f),
                        "measurement_status": f.measurement_status,
                        "attributes": f.properties,
                    },
                )
                for f in self.repo.features_for(record.id)
                if f.geometry is not None
            ]
        )

    def stats(self) -> StatsResponse:
        by_status = self.repo.count_files_by_status()
        geometry_counts = self.repo.count_features_by_geometry_type()
        return StatsResponse(
            files_total=sum(by_status.values()),
            files_completed=by_status.get(FileStatus.COMPLETED, 0),
            files_failed=by_status.get(FileStatus.FAILED, 0),
            features_total=sum(geometry_counts.values()),
            geometry_counts=geometry_counts,
        )

    def delete(self, file_id: uuid.UUID) -> None:
        record = self.get_file(file_id)
        stored_path = self.settings.upload_dir / record.stored_filename
        self.repo.delete(record)
        stored_path.unlink(missing_ok=True)

    def _completed_file(self, file_id: uuid.UUID) -> GeospatialFile:
        record = self.get_file(file_id)
        if record.status is not FileStatus.COMPLETED:
            raise FileNotReadyError(
                f"This file is {record.status.value}"
                + (f": {record.error_message}" if record.error_message else ".")
            )
        return record


def _measurement_of(feature) -> Measurement | None:
    if feature.measurement_type is None or feature.measurement_value is None:
        return None
    return Measurement(
        type=feature.measurement_type,
        value=feature.measurement_value,
        unit=feature.measurement_unit,
    )
