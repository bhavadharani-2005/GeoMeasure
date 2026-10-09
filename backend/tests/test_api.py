import io
import uuid
import zipfile
from unittest.mock import patch

import pytest
from pyproj import Geod
from shapely.geometry import GeometryCollection, Point

from .conftest import LINE, SQUARE, SQUARE_2, upload, write_kml, zip_shapefile

GEOD = Geod(ellps="WGS84")


def test_health(client):
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


def test_root_redirects_to_docs(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_upload_kml(client, kml_bytes):
    response = upload(client, "survey.kml", kml_bytes)
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "survey.kml"
    assert body["original_crs"] == "EPSG:4326"
    assert body["feature_count"] == 3
    assert body["status"] == "COMPLETED"
    uuid.UUID(body["id"])


def test_upload_zipped_shapefile(client, shapefile_zip):
    response = upload(client, "survey.zip", shapefile_zip, "application/zip")
    assert response.status_code == 201
    assert response.json()["feature_count"] == 2
    assert response.json()["original_crs"] == "EPSG:4326"


def test_file_information(client, kml_bytes):
    file_id = upload(client, "survey.kml", kml_bytes).json()["id"]
    body = client.get(f"/api/files/{file_id}/").json()
    assert body["id"] == file_id
    assert body["file_type"] == "kml"
    assert body["file_size"] == len(kml_bytes)
    assert body["crs"] == "EPSG:4326"
    assert body["projected_crs"] == "EPSG:32643"
    assert body["status"] == "COMPLETED"
    assert body["geometry_summary"] == {"Polygon": 1, "LineString": 1, "Point": 1}


def test_measurements_endpoint_returns_correct_values(client, kml_bytes):
    file_id = upload(client, "survey.kml", kml_bytes).json()["id"]
    body = client.get(f"/api/files/{file_id}/measurements/").json()
    by_type = {f["geometry_type"]: f for f in body["features"]}

    polygon = by_type["Polygon"]
    assert polygon["measurement"]["type"] == "area"
    assert polygon["measurement"]["unit"] == "m²"
    assert polygon["measurement"]["value"] == pytest.approx(
        abs(GEOD.geometry_area_perimeter(SQUARE)[0]), rel=0.005
    )
    assert polygon["properties"]["Name"] == "feature-0"
    assert polygon["crs"] == "EPSG:4326"
    assert polygon["geometry"]["type"] == "Polygon"

    line = by_type["LineString"]
    assert line["measurement"]["type"] == "length"
    assert line["measurement"]["unit"] == "m"
    assert line["measurement"]["value"] == pytest.approx(GEOD.geometry_length(LINE), rel=0.005)

    point = by_type["Point"]
    assert point["measurement"] is None
    assert point["measurement_status"] == "NOT_APPLICABLE"
    assert [f["feature_index"] for f in body["features"]] == [0, 1, 2]


def test_projected_shapefile_matches_geographic_shapefile(client, tmp_path):
    geographic = upload(client, "geo.zip", zip_shapefile(tmp_path / "a", [SQUARE_2])).json()
    projected = upload(
        client, "utm.zip", zip_shapefile(tmp_path / "b", [SQUARE_2], crs="EPSG:32643")
    ).json()
    assert projected["original_crs"] == "EPSG:32643"

    def area(file_id: str) -> float:
        features = client.get(f"/api/files/{file_id}/measurements/").json()["features"]
        return features[0]["measurement"]["value"]

    assert area(projected["id"]) == pytest.approx(area(geographic["id"]), rel=1e-6)


def test_line_shapefile_reports_length(client, tmp_path):
    file_id = upload(client, "lines.zip", zip_shapefile(tmp_path, [LINE])).json()["id"]
    feature = client.get(f"/api/files/{file_id}/measurements/").json()["features"][0]
    assert feature["geometry_type"] == "LineString"
    assert feature["measurement"]["value"] == pytest.approx(GEOD.geometry_length(LINE), rel=0.005)


def test_geojson_endpoint(client, kml_bytes):
    file_id = upload(client, "survey.kml", kml_bytes).json()["id"]
    body = client.get(f"/api/files/{file_id}/geojson/").json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 3
    assert body["features"][0]["properties"]["feature_index"] == 0


def test_list_files_newest_first(client, kml_bytes):
    first = upload(client, "one.kml", kml_bytes).json()["id"]
    second = upload(client, "two.kml", kml_bytes).json()["id"]
    listing = client.get("/api/files/").json()
    assert [f["id"] for f in listing] == [second, first]


def test_stats(client, kml_bytes):
    upload(client, "survey.kml", kml_bytes)
    stats = client.get("/api/stats/").json()
    assert stats["files_total"] == 1
    assert stats["features_total"] == 3
    assert stats["geometry_counts"]["Polygon"] == 1


def test_delete_removes_record_and_stored_file(client, kml_bytes, settings):
    file_id = upload(client, "survey.kml", kml_bytes).json()["id"]
    assert list(settings.upload_dir.iterdir())
    assert client.delete(f"/api/files/{file_id}/").status_code == 204
    assert client.get(f"/api/files/{file_id}/").status_code == 404
    assert not list(settings.upload_dir.iterdir())


# ---- error handling ---------------------------------------------------------


def assert_error(response, status: int, code: str):
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"]
    assert "Traceback" not in response.text


def test_unsupported_extension_rejected(client):
    assert_error(upload(client, "notes.txt", b"hello"), 400, "INVALID_FILE_TYPE")
    assert_error(upload(client, "shape.shp", b"hello"), 400, "INVALID_FILE_TYPE")


def test_empty_upload_rejected(client):
    assert_error(upload(client, "empty.kml", b""), 400, "EMPTY_FILE")


def test_oversized_upload_rejected(client, settings):
    too_big = b"0" * (settings.max_upload_bytes + 1)
    assert_error(upload(client, "big.kml", too_big), 413, "FILE_TOO_LARGE")
    assert not list(settings.upload_dir.iterdir())


def test_malformed_kml_marks_file_failed(client):
    response = upload(client, "broken.kml", b"<kml><Document><Placemark>not closed")
    assert_error(response, 422, "UNREADABLE_FILE")
    assert "/" not in response.json()["error"]["message"]  # no server paths leaked
    file_id = response.json()["error"]["details"]["file_id"]
    record = client.get(f"/api/files/{file_id}/").json()
    assert record["status"] == "FAILED"
    assert record["error_message"]


def test_invalid_zip_rejected(client):
    assert_error(upload(client, "bad.zip", b"definitely not a zip"), 422, "INVALID_ZIP")


def test_zip_without_shp_rejected(client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("readme.txt", "no shapefile here")
    assert_error(upload(client, "empty.zip", buffer.getvalue()), 422, "INVALID_SHAPEFILE")


def test_incomplete_shapefile_rejected(client, tmp_path):
    archive = zip_shapefile(tmp_path, [SQUARE], drop=(".dbf",))
    response = upload(client, "partial.zip", archive)
    assert_error(response, 422, "INVALID_SHAPEFILE")
    assert ".dbf" in response.json()["error"]["message"]


def test_malformed_shapefile_rejected(client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for ext in ("shp", "shx", "dbf"):
            archive.writestr(f"bad.{ext}", b"garbage bytes")
    assert_error(upload(client, "bad.zip", buffer.getvalue()), 422, "INVALID_SHAPEFILE")


def test_shapefile_without_prj_fails_with_missing_crs(client, tmp_path):
    archive = zip_shapefile(tmp_path, [SQUARE], drop=(".prj",))
    response = upload(client, "noprj.zip", archive)
    assert_error(response, 422, "MISSING_CRS")
    file_id = response.json()["error"]["details"]["file_id"]
    assert client.get(f"/api/files/{file_id}/measurements/").status_code == 409


def test_zip_path_traversal_rejected(client, settings, tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../../evil.shp", b"x")
    assert_error(upload(client, "evil.zip", buffer.getvalue()), 422, "INVALID_ZIP")
    assert not (tmp_path / "evil.shp").exists()


def test_zip_bomb_rejected(client, settings):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("big.dbf", b"0" * (2 * 1024 * 1024))
    assert buffer.tell() < settings.max_upload_bytes
    settings.max_extracted_mb = 1  # cap far below the 2 MB this archive expands to
    assert_error(upload(client, "bomb.zip", buffer.getvalue()), 422, "INVALID_ZIP")


def test_dataset_of_unsupported_geometries_still_succeeds(client, tmp_path):
    kml = write_kml(tmp_path / "mixed.kml", [SQUARE, GeometryCollection([Point(77.6, 12.9), LINE])])
    file_id = upload(client, "mixed.kml", kml).json()["id"]
    features = client.get(f"/api/files/{file_id}/measurements/").json()["features"]
    statuses = {f["geometry_type"]: f["measurement_status"] for f in features}
    assert statuses["Polygon"] == "MEASURED"
    assert "UNSUPPORTED" in statuses.values()


def test_unexpected_processing_failure_is_contained(client, kml_bytes):
    with patch("app.services.file_service.process_dataset", side_effect=RuntimeError("boom")):
        response = upload(client, "survey.kml", kml_bytes)
    assert_error(response, 500, "PROCESSING_FAILED")
    assert "boom" not in response.text
    file_id = response.json()["error"]["details"]["file_id"]
    assert client.get(f"/api/files/{file_id}/").json()["status"] == "FAILED"


def test_unknown_and_invalid_ids(client):
    missing = uuid.uuid4()
    for path in ("", "measurements/", "geojson/"):
        assert_error(client.get(f"/api/files/{missing}/{path}"), 404, "FILE_NOT_FOUND")
    assert_error(client.delete(f"/api/files/{missing}/"), 404, "FILE_NOT_FOUND")
    assert_error(client.get("/api/files/not-a-uuid/"), 422, "VALIDATION_ERROR")


def test_missing_multipart_field_is_a_validation_error(client):
    assert_error(client.post("/api/files/"), 422, "VALIDATION_ERROR")


def test_openapi_schema_builds(client):
    assert client.get("/openapi.json").status_code == 200
