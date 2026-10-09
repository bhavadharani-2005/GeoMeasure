from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import FileServiceDep
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.schemas.file import StatsResponse

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health/", summary="Service and database health")
def health(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unavailable", "version": settings.app_version},
        )
    return {"status": "ok", "database": "ok", "version": settings.app_version}


@router.get("/stats/", response_model=StatsResponse, summary="Aggregate counts across all files")
def stats(service: FileServiceDep):
    return service.stats()
