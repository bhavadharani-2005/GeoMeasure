import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import files, health
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Upload KML or zipped Shapefiles and get CRS-correct area/length measurements.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("/docs")

    app.include_router(health.router)
    app.include_router(files.router)
    return app


app = create_app()
