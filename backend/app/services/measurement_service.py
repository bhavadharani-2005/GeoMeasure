from dataclasses import dataclass
from enum import Enum
import logging

from shapely.errors import ShapelyError
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger(__name__)

AREA_UNIT = "m²"
LENGTH_UNIT = "m"


class MeasurementStatus(str, Enum):
    MEASURED = "MEASURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"  # e.g. points: nothing to measure
    UNSUPPORTED = "UNSUPPORTED"  # e.g. GeometryCollection
    EMPTY = "EMPTY"  # missing or empty geometry


@dataclass(frozen=True)
class MeasurementResult:
    status: MeasurementStatus
    type: str | None = None
    value: float | None = None
    unit: str | None = None


def measure_geometry(geometry: BaseGeometry | None) -> MeasurementResult:
    """Measure a geometry that is already in a projected, metre-based CRS."""
    if geometry is None or geometry.is_empty:
        return MeasurementResult(MeasurementStatus.EMPTY)
    try:
        match geometry.geom_type:
            case "Polygon" | "MultiPolygon":
                return _measured("area", geometry.area, AREA_UNIT)
            case "LineString" | "LinearRing" | "MultiLineString":
                return _measured("length", geometry.length, LENGTH_UNIT)
            case "Point" | "MultiPoint":
                return MeasurementResult(MeasurementStatus.NOT_APPLICABLE)
            case _:
                return MeasurementResult(MeasurementStatus.UNSUPPORTED)
    except ShapelyError:
        logger.warning("Could not measure %s geometry", geometry.geom_type, exc_info=True)
        return MeasurementResult(MeasurementStatus.UNSUPPORTED)


def _measured(kind: str, value: float, unit: str) -> MeasurementResult:
    return MeasurementResult(MeasurementStatus.MEASURED, kind, round(value, 6), unit)
