import uuid
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.geospatial_file import GeospatialFile

# JSONB on PostgreSQL, plain JSON elsewhere (SQLite dev fallback).
JsonType = JSON().with_variant(JSONB(), "postgresql")


class Feature(Base):
    __tablename__ = "features"
    __table_args__ = (UniqueConstraint("file_id", "feature_index", name="uq_feature_file_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("geospatial_files.id", ondelete="CASCADE"), index=True
    )
    feature_index: Mapped[int] = mapped_column(Integer)
    geometry_type: Mapped[str] = mapped_column(String(32), index=True)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    properties: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    measurement_status: Mapped[str] = mapped_column(String(16))
    measurement_type: Mapped[str | None] = mapped_column(String(16))
    measurement_value: Mapped[float | None] = mapped_column(Float)
    measurement_unit: Mapped[str | None] = mapped_column(String(8))

    file: Mapped[GeospatialFile] = relationship(back_populates="features")
