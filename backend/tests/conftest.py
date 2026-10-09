import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

import geopandas as gpd
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point, Polygon

from app.core.config import Settings, get_settings
from app.core.database import build_engine, get_db
from app.main import create_app
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Small shapes near Bengaluru (lat ~12.97): 0.001 degrees on each side.
SQUARE = Polygon([(77.590, 12.970), (77.591, 12.970), (77.591, 12.971), (77.590, 12.971)])
LINE = LineString([(77.590, 12.970), (77.592, 12.970)])
POINT = Point(77.595, 12.975)
SQUARE_2 = Polygon([(77.592, 12.972), (77.594, 12.972), (77.594, 12.974), (77.592, 12.974)])


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        upload_dir=tmp_path / "uploads",
        max_upload_mb=1,
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """API client backed by a throwaway database created through the real migrations."""
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")

    engine = build_engine(settings.database_url)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


def _frame(geometries, crs="EPSG:4326") -> gpd.GeoDataFrame:
    """Frame of lon/lat geometries, reprojected to ``crs`` if it is not EPSG:4326."""
    frame = gpd.GeoDataFrame(
        {"name": [f"feature-{i}" for i in range(len(geometries))]},
        geometry=list(geometries),
        crs="EPSG:4326",
    )
    return frame if crs == "EPSG:4326" else frame.to_crs(crs)


def write_kml(path: Path, geometries, crs="EPSG:4326") -> bytes:
    _frame(geometries, crs).to_file(path, driver="KML")
    return path.read_bytes()


def zip_shapefile(tmp_path: Path, geometries, crs="EPSG:4326", drop: tuple[str, ...] = ()) -> bytes:
    shp_dir = tmp_path / "shp_src"
    shp_dir.mkdir(parents=True, exist_ok=True)
    _frame(geometries, crs).to_file(shp_dir / "survey.shp")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for part in sorted(shp_dir.iterdir()):
            if part.suffix not in drop:
                archive.write(part, part.name)
    return buffer.getvalue()


@pytest.fixture
def kml_bytes(tmp_path: Path) -> bytes:
    return write_kml(tmp_path / "survey.kml", [SQUARE, LINE, POINT])


@pytest.fixture
def shapefile_zip(tmp_path: Path) -> bytes:
    return zip_shapefile(tmp_path, [SQUARE, SQUARE_2])


def upload(client: TestClient, name: str, content: bytes, content_type: str = "application/octet-stream"):
    return client.post("/api/files/", files={"file": (name, content, content_type)})
