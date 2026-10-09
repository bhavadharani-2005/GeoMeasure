# GeoMeasure

Spatial files. Reliable measurements.

GeoMeasure is a FastAPI service (plus a React interface) that accepts a KML file or a zipped Shapefile, extracts every feature, and calculates **CRS-correct** areas and lengths. Geometries in latitude/longitude are reprojected to a metre-based projected CRS before anything is measured.

## Features

- Upload `.kml` or `.zip` (Shapefile) with validation of type, size, archive contents and CRS
- Per-feature extraction: index, geometry type, geometry (GeoJSON), CRS, attributes
- Polygon area in m², LineString length in m, Points explicitly report "no measurement"
- Unsupported / empty geometries never fail the request: they get a `measurement_status` instead
- Persistent file history, GeoJSON endpoint for mapping, delete with stored-file cleanup
- Consistent JSON errors with stable error codes; server-side logging, no tracebacks to clients
- React UI: overview, drag-and-drop upload, file list, file details with Leaflet map, measurement table and feature inspector
- 48 pytest tests; migrations verified on SQLite and PostgreSQL 16

## Tech stack

| Layer | Choice |
| --- | --- |
| API | Python 3.12+, FastAPI, Pydantic v2, Uvicorn |
| Data | SQLAlchemy 2.x, Alembic, PostgreSQL (SQLite as a dev/test fallback) |
| GIS | GeoPandas, Shapely, PyProj, pyogrio |
| Frontend | React 19, TypeScript, Vite, React Router, Axios, Leaflet, Lucide, custom CSS |
| Tests | pytest, FastAPI TestClient |

## Architecture

```
HTTP route  ->  FileService  ->  geospatial_service  ->  crs_service
(files.py)      (orchestrate)    (read + extract)        (pick measurement CRS)
                     |                  |
                     |                  +-> measurement_service (area / length)
                     +-> FileRepository (SQLAlchemy queries)
```

- **Routes** (`api/routes`) are thin: parse input, call the service, return a schema.
- **`FileService`** owns the upload workflow and status transitions (`PROCESSING` -> `COMPLETED` / `FAILED`).
- **`geospatial_service`** reads files and builds features. **`crs_service`** and **`measurement_service`** are pure GIS logic with no HTTP or database knowledge, so they are easy to unit test.
- **`FileRepository`** is the only place that writes SQL.
- **`core/exceptions.py`** defines typed `AppError`s; one handler turns them into `{"error": {"code", "message"}}`.

### Upload flow

1. Validate extension (`.kml`, `.zip`) and sanitise the filename.
2. Stream the body to a generated name (`<uuid>.<ext>`) in the upload directory, enforcing the size limit while streaming, rejecting empty files.
3. Insert the `geospatial_files` row with status `PROCESSING`.
4. Process (below). On success, bulk-insert features and mark `COMPLETED`. On failure, mark `FAILED`, store a user-safe message, delete the stored upload, and return the error.

### Processing flow

- **KML:** every non-empty layer (KML folders become layers) is read with pyogrio and merged. A `layer` attribute is added when there is more than one.
- **Shapefile:** the ZIP is extracted into a temporary directory that is always removed. Only known Shapefile parts (`.shp .shx .dbf .prj .cpg ...`) are written; everything else is ignored. Protection against path traversal (`..`, absolute paths, drive letters), symlinks, encrypted members, too many members, and zip bombs (decompressed size is counted while streaming, not trusted from headers). Exactly one `.shp` with `.shx` and `.dbf` is required.
- Features are extracted in file order; the geometry is stored as GeoJSON in EPSG:4326 (what Leaflet needs), attributes as JSON.

### Measurement and CRS flow

`crs_service.plan_measurement_crs` decides which CRS to measure in:

1. **No CRS** -> `MISSING_CRS` error. A CRS is never guessed, because a guessed CRS silently produces wrong numbers.
2. **Already a projected CRS in metres** (and not Web Mercator) -> use it as is.
3. **Anything else** (geographic CRS like EPSG:4326, feet-based CRS, Web Mercator) -> `GeoDataFrame.estimate_utm_crs()` picks the UTM zone from the dataset's extent and the data is reprojected to it.

`measurement_service.measure_geometry` then runs on the projected geometry:

| Geometry | Result |
| --- | --- |
| Polygon / MultiPolygon | `area` in `m²` |
| LineString / MultiLineString | `length` in `m` |
| Point / MultiPoint | `measurement: null`, status `NOT_APPLICABLE` |
| GeometryCollection, other | `measurement: null`, status `UNSUPPORTED` |
| Empty / missing | `measurement: null`, status `EMPTY` |

Canonical values are stored in m² and m. The UI shows ha / km² / km as a convenience only.

### Database

```
geospatial_files 1 ──< features
```

- `geospatial_files`: `id` (UUID), original and stored filename, `file_type`, `file_size`, `original_crs`, `projected_crs`, `feature_count`, `status`, `error_message`, `created_at`, `updated_at`
- `features`: `file_id` (FK, `ON DELETE CASCADE`), `feature_index` (unique per file), `geometry_type`, `geometry` (JSONB on PostgreSQL), `properties` (JSONB), `measurement_status/type/value/unit`

## Project structure

```
backend/
  app/
    main.py                 app factory, CORS, routers
    core/                   config, database, exceptions
    api/                    deps.py, routes/{files,health}.py
    models/                 SQLAlchemy models
    schemas/                Pydantic response models
    services/               file, geospatial, crs, measurement
    repositories/           file_repository.py
    utils/file_validation.py  filename + ZIP safety
  alembic/                  migrations
  tests/
frontend/
  src/{api,components,hooks,pages,styles,types,utils}
docker-compose.yml
```

## Local setup

Requires Python 3.12+ and Node 20+.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows cmd: .venv\Scripts\activate   PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env               # Windows cmd: copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

API: http://localhost:8000 · Swagger UI: http://localhost:8000/docs

**Database.** `.env.example` defaults to SQLite (`sqlite:///./geomeasure.db`), so the steps above work without installing anything. To use PostgreSQL (the intended production database), uncomment the `postgresql+psycopg://geomeasure:geomeasure@localhost:5432/geomeasure` line in `.env`, create that role and database (or run `docker compose up db`), then run `alembic upgrade head` again. Both databases use the same models and migration.

| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | SQLite file | SQLAlchemy URL |
| `UPLOAD_DIR` | `./storage/uploads` | Where uploads are kept |
| `MAX_UPLOAD_MB` | `25` | Upload size limit |
| `MAX_EXTRACTED_MB` | `200` | Max decompressed size of a ZIP |
| `MAX_FEATURES` | `20000` | Max features per dataset |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed browser origins |

### Frontend

```bash
cd frontend
npm install
cp .env.example .env          # Windows cmd: copy .env.example .env  (VITE_API_BASE_URL=http://localhost:8000)
npm run dev                   # http://localhost:5173
npm run build                 # type-check + production build
```

## Docker

```bash
docker compose up --build
```

Starts PostgreSQL, the API (runs migrations on start) at http://localhost:8000 and the UI at http://localhost:5173. *Note: the compose file passes `docker compose config` validation, but the images were not built in the environment this project was developed in, so treat the Docker setup as untested.*

## API

All paths accept a trailing slash as shown. Errors always look like:

```json
{ "error": { "code": "INVALID_FILE_TYPE", "message": "Only .kml and zipped Shapefiles (.zip) are supported." } }
```

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/files/` | Upload and process a file (`multipart/form-data`, field `file`) |
| GET | `/api/files/` | File history, newest first (`limit`, `offset`) |
| GET | `/api/files/{id}/` | File metadata |
| GET | `/api/files/{id}/measurements/` | Features with measurements |
| GET | `/api/files/{id}/geojson/` | Features as a GeoJSON FeatureCollection (EPSG:4326) |
| DELETE | `/api/files/{id}/` | Delete record, features and stored upload (204) |
| GET | `/api/stats/` | Aggregate counts used by the overview page |
| GET | `/api/health/` | Service and database health |

### Upload

```bash
curl -F "file=@survey.kml" http://localhost:8000/api/files/
```

`201 Created`

```json
{
  "id": "6410757d-468b-41e7-aa0b-38b99c131bd8",
  "filename": "survey.kml",
  "original_crs": "EPSG:4326",
  "feature_count": 3,
  "status": "COMPLETED",
  "created_at": "2026-10-08T04:26:34.466603Z"
}
```

### File information

`GET /api/files/{id}/`

```json
{
  "id": "6410757d-468b-41e7-aa0b-38b99c131bd8",
  "filename": "survey.kml",
  "file_type": "kml",
  "file_size": 880,
  "feature_count": 3,
  "original_crs": "EPSG:4326",
  "crs": "EPSG:4326",
  "projected_crs": "EPSG:32643",
  "status": "COMPLETED",
  "error_message": null,
  "geometry_summary": { "Polygon": 1, "LineString": 1, "Point": 1 },
  "created_at": "2026-10-08T04:26:34.466603Z",
  "updated_at": "2026-10-08T04:26:34.466603Z"
}
```

### Measurements

`GET /api/files/{id}/measurements/` (geometry abbreviated)

```json
{
  "file_id": "6410757d-468b-41e7-aa0b-38b99c131bd8",
  "original_crs": "EPSG:4326",
  "projected_crs": "EPSG:32643",
  "geometry_crs": "EPSG:4326",
  "feature_count": 3,
  "features": [
    {
      "feature_index": 0,
      "geometry_type": "Polygon",
      "geometry": { "type": "Polygon", "coordinates": ["..."] },
      "crs": "EPSG:4326",
      "properties": { "Name": "Parcel" },
      "measurement": { "type": "area", "value": 12016.970249, "unit": "m²" },
      "measurement_status": "MEASURED"
    },
    {
      "feature_index": 1,
      "geometry_type": "LineString",
      "properties": { "Name": "Road" },
      "measurement": { "type": "length", "value": 1009.252734, "unit": "m" },
      "measurement_status": "MEASURED"
    },
    {
      "feature_index": 2,
      "geometry_type": "Point",
      "properties": { "Name": "Gate" },
      "measurement": null,
      "measurement_status": "NOT_APPLICABLE"
    }
  ]
}
```

Features keep their original attributes. `geometry` is always GeoJSON in EPSG:4326 and `crs` is the file's original CRS.

### Error codes

| HTTP | Code | When |
| --- | --- | --- |
| 400 | `INVALID_FILE_TYPE` | Extension is not `.kml` / `.zip` |
| 400 | `EMPTY_FILE` | Zero-byte upload |
| 404 | `FILE_NOT_FOUND` | Unknown id |
| 409 | `FILE_NOT_PROCESSED` | Measurements requested for a `FAILED` file |
| 413 | `FILE_TOO_LARGE` | Over `MAX_UPLOAD_MB` |
| 422 | `INVALID_ZIP` | Not a ZIP, corrupt, unsafe paths, too large when unpacked |
| 422 | `INVALID_SHAPEFILE` | No `.shp`, missing `.shx`/`.dbf`, several Shapefiles, unreadable |
| 422 | `UNREADABLE_FILE` | KML could not be parsed |
| 422 | `MISSING_CRS` | Dataset has no CRS (e.g. Shapefile without `.prj`) |
| 422 | `EMPTY_DATASET` / `TOO_MANY_FEATURES` | No usable geometry / above `MAX_FEATURES` |
| 422 | `VALIDATION_ERROR` | Malformed request or id |
| 500 | `PROCESSING_FAILED` | Unexpected error (logged server-side) |

A file that fails processing is kept in the history as `FAILED` with its error message, and the error response includes its `file_id`.

## Testing

```bash
cd backend
pytest
```

The suite builds its KML and Shapefile fixtures on the fly, creates a throwaway SQLite database through the real Alembic migration, and covers: health, KML and Shapefile upload, projected vs geographic inputs, file info, measurements, GeoJSON, list/stats/delete, every error path above (including ZIP traversal and a zip bomb), unsupported geometries, contained processing failures, 404s, OpenAPI generation, attribute types (dates, NaN, unicode), 3D and multi-folder KML, nested/uppercase ZIP layouts, CORS and filename sanitising. Area and length results are compared against an independent ellipsoidal calculation (`pyproj.Geod`).

## CRS and measurement strategy

- **Degrees are not distances.** In EPSG:4326, one degree of longitude is ~111 km at the equator and shrinks toward the poles, so `.area` / `.length` on lon/lat coordinates return meaningless "square degrees". (The test fixtures show this: a ~12,000 m² plot has a degree-space area around `1e-6`.)
- **A projected CRS in metres is required.** It maps the ground to a plane where Shapely's planar `.area` and `.length` are valid.
- **UTM is chosen from the data.** `estimate_utm_crs()` selects the zone for the dataset's extent. UTM is conformal and keeps scale error small (roughly 0.04% near the zone centre, growing toward the edges), which is a good fit for parcel- and survey-sized data. Compared with a geodesic calculation, test results differ by about 0.1%.
- **Web Mercator is not used for measuring.** It is projected and metre-based, but its scale distortion grows rapidly with latitude, so it is treated as unsuitable and replaced by UTM.
- **No CRS means no measurement.** The request fails with `MISSING_CRS` rather than assuming WGS84.
- Limitation: a dataset spanning several UTM zones is measured in the single zone estimated for its overall extent, so accuracy degrades for very large or global datasets.

## Design decisions

- **FastAPI:** typed request/response models, automatic OpenAPI docs, simple dependency injection.
- **SQLAlchemy + Alembic + PostgreSQL:** relational model with a cascading foreign key; JSONB for variable GIS attributes. SQLite works as a fallback, using the same models and migration.
- **No PostGIS:** geometry is stored as GeoJSON and all spatial maths happens in GeoPandas/Shapely. No spatial queries are needed, so PostGIS would add infrastructure without adding capability.
- **Synchronous processing:** simplest architecture and sufficient for assignment-sized files; the client gets the result in one request and there is no job/poll protocol to explain. The limits (`MAX_UPLOAD_MB`, `MAX_FEATURES`) bound the work per request. For large datasets, `_process` is a single seam to move behind a task queue.
- **No Redis/Celery:** nothing requires them at this scope.
- **Service separation:** CRS and measurement code never touches HTTP or the database.
- **Measurement stored with the feature:** computed once at upload; reads are plain SQL.
- **Status model:** a `FAILED` row is kept so a user can see what went wrong in the file history.
- **Frontend:** plain custom CSS with design tokens, a small typed Axios client; no component library.

## Learning

- GIS formats are less uniform than they look: KML folders are separate layers and carry many empty boilerplate fields, while a Shapefile is a bundle of files where a missing `.prj` silently removes the CRS.
- CRS handling is where silent bugs live. Reprojecting before measuring, refusing to guess a missing CRS, and testing against an independent geodesic calculation made the numbers trustworthy.
- Untrusted ZIPs need defence in depth: validate names, skip what is not needed, and count decompressed bytes as they stream.
- Keeping GIS logic as pure functions made the hardest part of the system the easiest to test.

## Future scope

None of the following is implemented.

- Asynchronous processing and progress reporting for very large datasets
- Cloud object storage for uploads
- PostGIS for spatial queries (bounding box, intersects)
- Background task queue (Celery/RQ)
- More formats (GeoJSON, GeoPackage, KMZ) and multi-layer Shapefile bundles
- Batch uploads
- Authentication and authorisation
- Measurement export (CSV / GeoJSON)
- Geodesic measurement option for datasets spanning multiple UTM zones
