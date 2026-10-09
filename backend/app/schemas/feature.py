import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.measurement import Measurement


class FeatureMeasurement(BaseModel):
    feature_index: int
    geometry_type: str
    geometry: dict[str, Any] | None
    crs: str | None
    properties: dict[str, Any]
    measurement: Measurement | None
    measurement_status: str


class MeasurementsResponse(BaseModel):
    file_id: uuid.UUID
    original_crs: str | None
    projected_crs: str | None
    geometry_crs: str = "EPSG:4326"
    feature_count: int
    features: list[FeatureMeasurement]


class GeoJsonFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any]
    properties: dict[str, Any]


class GeoJsonFeatureCollection(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"type": "FeatureCollection"}})

    type: str = "FeatureCollection"
    features: list[GeoJsonFeature]
