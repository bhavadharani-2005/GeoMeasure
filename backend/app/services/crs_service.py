"""CRS strategy: decide which projected, metre-based CRS measurements are made in.

Latitude/longitude degrees are angles, not lengths: one degree of longitude is
~111 km at the equator and shrinks to zero at the poles. Calling ``.area`` or
``.length`` on EPSG:4326 geometry therefore returns meaningless "square degrees".
Geometries must be projected first.
"""

from dataclasses import dataclass

import geopandas as gpd
from pyproj import CRS

from app.core.exceptions import EmptyDatasetError, MissingCrsError

# Projections whose scale distortion is too large for area/length work.
_DISTORTING_METHOD_MARKERS = ("pseudo mercator", "popular visualisation")


@dataclass(frozen=True)
class CrsPlan:
    source: CRS
    measurement: CRS

    @property
    def source_label(self) -> str:
        return crs_label(self.source)

    @property
    def measurement_label(self) -> str:
        return crs_label(self.measurement)

    @property
    def needs_reprojection(self) -> bool:
        return not self.source.equals(self.measurement)


def crs_label(crs: CRS) -> str:
    authority = crs.to_authority()
    return f"{authority[0]}:{authority[1]}" if authority else crs.name


def is_suitable_for_measurement(crs: CRS) -> bool:
    """True for projected CRSs whose axes are metres and that are not web Mercator."""
    if not crs.is_projected:
        return False
    if any(axis.unit_conversion_factor != 1.0 for axis in crs.axis_info):
        return False
    method = (crs.coordinate_operation.method_name if crs.coordinate_operation else "").lower()
    return not any(marker in method for marker in _DISTORTING_METHOD_MARKERS)


def plan_measurement_crs(gdf: gpd.GeoDataFrame) -> CrsPlan:
    """Choose the CRS to measure in, never guessing a missing source CRS."""
    if gdf.crs is None:
        raise MissingCrsError()
    source = CRS.from_user_input(gdf.crs)
    if is_suitable_for_measurement(source):
        return CrsPlan(source=source, measurement=source)
    if gdf.geometry.is_empty.all() or gdf.geometry.isna().all():
        raise EmptyDatasetError()
    # UTM zone chosen from the dataset's extent: accurate, locally conformal, in metres.
    return CrsPlan(source=source, measurement=gdf.estimate_utm_crs())
