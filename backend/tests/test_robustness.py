"""Awkward-but-realistic inputs: attribute types, 3D coordinates, layout of ZIPs, CORS."""

import io
import zipfile
from datetime import date

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Point

from .conftest import SQUARE, SQUARE_2, upload


def _zip_dir(directory, prefix="", rename=lambda name: name) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for part in sorted(directory.iterdir()):
            archive.write(part, f"{prefix}{rename(part.name)}")
    return buffer.getvalue()


def test_shapefile_attribute_types_are_serialised(client, tmp_path):
    frame = gpd.GeoDataFrame(
        {
            "name": ["Zażółć — plot", None],
            "area_ha": [1.5, np.nan],
            "count": [3, 4],
            "surveyed": [date(2024, 5, 1), date(2025, 1, 2)],
        },
        geometry=[SQUARE, SQUARE_2],
        crs="EPSG:4326",
    )
    frame.to_file(tmp_path / "attrs.shp")
    response = upload(client, "attrs.zip", _zip_dir(tmp_path))
    assert response.status_code == 201, response.text
    features = client.get(f"/api/files/{response.json()['id']}/measurements/").json()["features"]
    assert features[0]["properties"]["name"] == "Zażółć — plot"
    assert features[1]["properties"]["area_ha"] is None
    assert features[0]["properties"]["count"] == 3
    assert "2024-05-01" in str(features[0]["properties"]["surveyed"])


def test_kml_with_altitude_and_several_folders(client, tmp_path):
    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Folder><name>Parcels</name><Placemark><name>P1</name><Polygon><outerBoundaryIs><LinearRing><coordinates>
77.590,12.970,900 77.591,12.970,900 77.591,12.971,900 77.590,12.971,900 77.590,12.970,900
</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></Folder>
<Folder><name>Roads</name><Placemark><name>R1</name><LineString><coordinates>
77.590,12.970,900 77.592,12.970,905
</coordinates></LineString></Placemark></Folder>
</Document></kml>"""
    response = upload(client, "layers.kml", kml.encode())
    assert response.status_code == 201, response.text
    assert response.json()["feature_count"] == 2
    features = client.get(f"/api/files/{response.json()['id']}/measurements/").json()["features"]
    by_type = {f["geometry_type"]: f for f in features}
    assert by_type["Polygon"]["measurement"]["value"] > 10_000
    assert by_type["LineString"]["measurement"]["value"] == pytest.approx(217, rel=0.02)
    assert {f["properties"]["layer"] for f in features} == {"Parcels", "Roads"}


def test_shapefile_in_nested_folder_with_uppercase_names(client, tmp_path):
    gpd.GeoDataFrame({"id": [1]}, geometry=[SQUARE], crs="EPSG:4326").to_file(tmp_path / "plot.shp")
    archive = _zip_dir(tmp_path, prefix="export/data/", rename=lambda n: n.upper())
    response = upload(client, "nested.zip", archive)
    assert response.status_code == 201, response.text
    assert response.json()["feature_count"] == 1


def test_zip_with_macos_metadata_is_accepted(client, tmp_path):
    gpd.GeoDataFrame({"id": [1]}, geometry=[SQUARE], crs="EPSG:4326").to_file(tmp_path / "plot.shp")
    buffer = io.BytesIO(_zip_dir(tmp_path))
    with zipfile.ZipFile(buffer, "a") as archive:
        archive.writestr("__MACOSX/._plot.shp", b"junk")
    assert upload(client, "mac.zip", buffer.getvalue()).status_code == 201


def test_point_shapefile_has_no_measurements(client, tmp_path):
    gpd.GeoDataFrame({"id": [1]}, geometry=[Point(77.59, 12.97)], crs="EPSG:4326").to_file(
        tmp_path / "pts.shp"
    )
    file_id = upload(client, "pts.zip", _zip_dir(tmp_path)).json()["id"]
    feature = client.get(f"/api/files/{file_id}/measurements/").json()["features"][0]
    assert feature["measurement"] is None and feature["measurement_status"] == "NOT_APPLICABLE"


def test_cors_preflight_allows_local_frontend(client):
    response = client.options(
        "/api/files/",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_unknown_origin(client):
    response = client.options(
        "/api/files/",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in response.headers


def test_urls_work_without_trailing_slash(client, kml_bytes):
    file_id = upload(client, "survey.kml", kml_bytes).json()["id"]
    assert client.get(f"/api/files/{file_id}").status_code == 200
    assert client.get("/api/health").status_code == 200


def test_filename_with_path_and_odd_characters_is_sanitised(client, kml_bytes):
    response = upload(client, "../../etc/passwd survey (1).kml", kml_bytes)
    assert response.status_code == 201
    assert "/" not in response.json()["filename"] and ".." not in response.json()["filename"]
