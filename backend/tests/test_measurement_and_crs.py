"""Unit tests for the GIS core: CRS planning and measurement, without HTTP or a database."""

import geopandas as gpd
import pytest
from pyproj import CRS, Geod
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Polygon

from app.core.exceptions import EmptyDatasetError, MissingCrsError
from app.services.crs_service import is_suitable_for_measurement, plan_measurement_crs
from app.services.geospatial_service import build_dataset
from app.services.measurement_service import MeasurementStatus, measure_geometry

from .conftest import LINE, POINT, SQUARE

GEOD = Geod(ellps="WGS84")


def geodesic_area(polygon: Polygon) -> float:
    return abs(GEOD.geometry_area_perimeter(polygon)[0])


def geodesic_length(line: LineString) -> float:
    return GEOD.geometry_length(line)


def test_geographic_crs_is_reprojected_to_utm():
    gdf = gpd.GeoDataFrame(geometry=[SQUARE], crs="EPSG:4326")
    plan = plan_measurement_crs(gdf)
    assert plan.needs_reprojection
    assert plan.measurement.is_projected
    assert plan.measurement_label == "EPSG:32643"  # UTM zone 43N covers Bengaluru


def test_metre_based_projected_crs_is_used_as_is():
    gdf = gpd.GeoDataFrame(geometry=[SQUARE], crs="EPSG:4326").to_crs("EPSG:32643")
    plan = plan_measurement_crs(gdf)
    assert not plan.needs_reprojection
    assert plan.measurement_label == "EPSG:32643"


def test_web_mercator_is_not_trusted_for_measurement():
    assert not is_suitable_for_measurement(CRS.from_epsg(3857))
    assert not is_suitable_for_measurement(CRS.from_epsg(4326))
    assert not is_suitable_for_measurement(CRS.from_epsg(2272))  # US survey feet


def test_missing_crs_raises_instead_of_guessing():
    with pytest.raises(MissingCrsError):
        plan_measurement_crs(gpd.GeoDataFrame(geometry=[SQUARE], crs=None))


def test_polygon_area_matches_geodesic_reference():
    dataset = build_dataset(gpd.GeoDataFrame(geometry=[SQUARE], crs="EPSG:4326"), 100)
    measurement = dataset.features[0].measurement
    assert measurement.type == "area" and measurement.unit == "m²"
    assert measurement.value == pytest.approx(geodesic_area(SQUARE), rel=0.005)
    # Naive degree maths would give ~1e-6: the reprojection is what makes this ~12,000.
    assert measurement.value > 10_000


def test_line_length_matches_geodesic_reference():
    dataset = build_dataset(gpd.GeoDataFrame(geometry=[LINE], crs="EPSG:4326"), 100)
    measurement = dataset.features[0].measurement
    assert measurement.type == "length" and measurement.unit == "m"
    assert measurement.value == pytest.approx(geodesic_length(LINE), rel=0.005)


def test_projected_input_gives_same_result_as_geographic_input():
    geographic = build_dataset(gpd.GeoDataFrame(geometry=[SQUARE], crs="EPSG:4326"), 100)
    projected = build_dataset(
        gpd.GeoDataFrame(geometry=[SQUARE], crs="EPSG:4326").to_crs("EPSG:32643"), 100
    )
    assert projected.features[0].measurement.value == pytest.approx(
        geographic.features[0].measurement.value, rel=1e-6
    )


def test_point_has_no_measurement():
    result = measure_geometry(POINT)
    assert result.status is MeasurementStatus.NOT_APPLICABLE
    assert result.type is None and result.value is None


def test_multipolygon_area_is_sum_of_parts():
    other = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    result = measure_geometry(MultiPolygon([other, Polygon([(20, 0), (30, 0), (30, 10)])]))
    assert result.value == pytest.approx(150.0)


def test_unsupported_and_empty_geometries_do_not_raise():
    assert measure_geometry(GeometryCollection([POINT, LINE])).status is MeasurementStatus.UNSUPPORTED
    assert measure_geometry(Polygon()).status is MeasurementStatus.EMPTY
    assert measure_geometry(None).status is MeasurementStatus.EMPTY


def test_dataset_keeps_features_with_missing_geometry():
    gdf = gpd.GeoDataFrame({"name": ["a", "b"]}, geometry=[SQUARE, None], crs="EPSG:4326")
    features = build_dataset(gdf, 100).features
    assert [f.geometry_type for f in features] == ["Polygon", "Empty"]
    assert features[1].geometry is None
    assert features[1].measurement.status is MeasurementStatus.EMPTY


def test_all_empty_dataset_is_rejected():
    gdf = gpd.GeoDataFrame(geometry=[None, None], crs="EPSG:4326")
    with pytest.raises(EmptyDatasetError):
        build_dataset(gdf, 100)
