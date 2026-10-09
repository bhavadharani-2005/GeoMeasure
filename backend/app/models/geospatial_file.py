import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.feature import Feature


class FileStatus(str, enum.Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FileType(str, enum.Enum):
    KML = "kml"
    SHAPEFILE = "shapefile"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class GeospatialFile(Base):
    __tablename__ = "geospatial_files"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[FileType] = mapped_column(Enum(FileType, native_enum=False, length=16))
    file_size: Mapped[int] = mapped_column(BigInteger)
    original_crs: Mapped[str | None] = mapped_column(String(255))
    projected_crs: Mapped[str | None] = mapped_column(String(255))
    feature_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[FileStatus] = mapped_column(
        Enum(FileStatus, native_enum=False, length=16), default=FileStatus.PROCESSING, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    features: Mapped[list["Feature"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Feature.feature_index",
    )

    @property
    def filename(self) -> str:
        return self.original_filename
