"""Read geospatial files and turn them into measured, JSON-ready features."""

import json
import logging
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import pyogrio
from pyogrio.errors import DataLayerError, DataSourceError

from app.core.config import Settings
from app.core.exceptions import (
    EmptyDatasetError,
    InvalidShapefileError,
    TooManyFeaturesError,
    UnreadableFileError,
)
from app.models.geospatial_file import FileType
from app.services.crs_service import plan_measurement_crs
from app.services.measurement_service import MeasurementResult, measure_geometry
from app.utils.file_validation import extract_shapefile

logger = logging.getLogger(__name__)

GEOJSON_CRS = "EPSG:4326"
EMPTY_GEOMETRY_TYPE = "Empty"
LAYER_PROPERTY = "layer"


@dataclass
class ProcessedFeature:
    feature_index: int
    geometry_type: str
    geometry: dict[str, Any] | None  # GeoJSON geometry in EPSG:4326
    properties: dict[str, Any]
    measurement: MeasurementResult


@dataclass
class ProcessedDataset:
    original_crs: str
    projected_crs: str
    features: list[ProcessedFeature] = field(default_factory=list)


def process_dataset(path: Path, file_type: FileType, settings: Settings) -> ProcessedDataset:
    if file_type is FileType.SHAPEFILE:
        with tempfile.TemporaryDirectory(prefix="geomeasure_") as workdir:
            shp_path = extract_shapefile(path, Path(workdir), settings.max_extracted_bytes)
            gdf = _read_layers(shp_path, wrap_error=InvalidShapefileError)
    else:
        gdf = _read_layers(path, wrap_error=UnreadableFileError)
    return build_dataset(gdf, settings.max_features)


def _read_layers(path: Path, wrap_error: type[Exception]) -> gpd.GeoDataFrame:
    """Read every non-empty layer (KML folders are separate layers) into one frame."""
    try:
        layer_names = [str(name) for name, _ in pyogrio.list_layers(path)]
        frames = [pyogrio.read_dataframe(path, layer=name) for name in layer_names]
    except (DataSourceError, DataLayerError) as exc:
        logger.info("Unreadable geospatial file %s: %s", path.name, exc)
        raise wrap_error(f"The file could not be read as geospatial data: {_short(exc)}") from exc

    non_empty = [(name, frame) for name, frame in zip(layer_names, frames) if len(frame)]
    if not non_empty:
        raise EmptyDatasetError()
    if len(non_empty) > 1:
        for name, frame in non_empty:
            frame[LAYER_PROPERTY] = name
    merged = pd.concat([frame for _, frame in non_empty], ignore_index=True)
    return gpd.GeoDataFrame(merged, geometry="geometry", crs=non_empty[0][1].crs)


def build_dataset(gdf: gpd.GeoDataFrame, max_features: int) -> ProcessedDataset:
    """Measure in a suitable projected CRS and emit GeoJSON-ready features."""
    if gdf.empty:
        raise EmptyDatasetError()
    if len(gdf) > max_features:
        raise TooManyFeaturesError(
            f"The dataset has {len(gdf)} features; the limit is {max_features}."
        )

    plan = plan_measurement_crs(gdf)
    projected = gdf.to_crs(plan.measurement) if plan.needs_reprojection else gdf
    geojson_features = json.loads(gdf.to_crs(GEOJSON_CRS).to_json(drop_id=True))["features"]

    features = []
    for index, (geometry, geojson) in enumerate(zip(projected.geometry, geojson_features)):
        has_geometry = geometry is not None and not geometry.is_empty
        features.append(
            ProcessedFeature(
                feature_index=index,
                geometry_type=geometry.geom_type if has_geometry else EMPTY_GEOMETRY_TYPE,
                geometry=geojson["geometry"] if has_geometry else None,
                properties=geojson["properties"] or {},
                measurement=measure_geometry(geometry),
            )
        )
    return ProcessedDataset(plan.source_label, plan.measurement_label, features)


_SERVER_PATH = re.compile(r"(?:[A-Za-z]:)?(?:[\\/][^\s:\\/]+)+")


def _short(exc: Exception, limit: int = 160) -> str:
    """One-line driver message with server filesystem paths removed."""
    text = _SERVER_PATH.sub("<file>", " ".join(str(exc).split()))
    return text if len(text) <= limit else f"{text[: limit - 1]}…"
