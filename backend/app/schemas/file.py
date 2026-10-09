import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

from app.models.geospatial_file import FileStatus, FileType


class _UtcModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", "updated_at", check_fields=False)
    @classmethod
    def _assume_utc(cls, value: datetime) -> datetime:
        # SQLite returns naive datetimes; everything is stored as UTC.
        return value if value.tzinfo else value.replace(tzinfo=UTC)


class FileUploadResponse(_UtcModel):
    id: uuid.UUID
    filename: str
    original_crs: str | None
    feature_count: int
    status: FileStatus
    created_at: datetime


class FileSummary(_UtcModel):
    id: uuid.UUID
    filename: str
    file_type: FileType
    file_size: int
    feature_count: int
    original_crs: str | None
    projected_crs: str | None
    status: FileStatus
    error_message: str | None
    created_at: datetime
    geometry_summary: dict[str, int] = {}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def crs(self) -> str | None:
        """Alias of ``original_crs`` matching the assignment's example payload."""
        return self.original_crs


class FileDetail(FileSummary):
    updated_at: datetime


class StatsResponse(BaseModel):
    files_total: int
    files_completed: int
    files_failed: int
    features_total: int
    geometry_counts: dict[str, int]
