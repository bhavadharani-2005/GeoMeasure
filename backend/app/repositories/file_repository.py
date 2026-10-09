import uuid
from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.models import Feature, FileStatus, GeospatialFile


class FileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, file: GeospatialFile) -> GeospatialFile:
        self.session.add(file)
        self.session.commit()
        return file

    def save(self, file: GeospatialFile) -> GeospatialFile:
        self.session.commit()
        return file

    def get(self, file_id: uuid.UUID) -> GeospatialFile | None:
        return self.session.get(GeospatialFile, file_id)

    def list_recent(self, limit: int, offset: int) -> Sequence[GeospatialFile]:
        stmt = (
            select(GeospatialFile)
            .order_by(GeospatialFile.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return self.session.scalars(stmt).all()

    def delete(self, file: GeospatialFile) -> None:
        self.session.delete(file)
        self.session.commit()

    def add_features(self, file_id: uuid.UUID, rows: list[dict]) -> None:
        if rows:
            self.session.execute(insert(Feature), [{**row, "file_id": file_id} for row in rows])

    def features_for(self, file_id: uuid.UUID) -> Sequence[Feature]:
        stmt = select(Feature).where(Feature.file_id == file_id).order_by(Feature.feature_index)
        return self.session.scalars(stmt).all()

    def geometry_summaries(self, file_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
        """Count features per geometry type for each file with one grouped query."""
        summaries: dict[uuid.UUID, dict[str, int]] = defaultdict(dict)
        if not file_ids:
            return summaries
        stmt = (
            select(Feature.file_id, Feature.geometry_type, func.count())
            .where(Feature.file_id.in_(file_ids))
            .group_by(Feature.file_id, Feature.geometry_type)
        )
        for file_id, geometry_type, count in self.session.execute(stmt):
            summaries[file_id][geometry_type] = count
        return summaries

    def count_files_by_status(self) -> dict[FileStatus, int]:
        stmt = select(GeospatialFile.status, func.count()).group_by(GeospatialFile.status)
        return {status: count for status, count in self.session.execute(stmt)}

    def count_features_by_geometry_type(self) -> dict[str, int]:
        stmt = select(Feature.geometry_type, func.count()).group_by(Feature.geometry_type)
        return {geometry_type: count for geometry_type, count in self.session.execute(stmt)}
