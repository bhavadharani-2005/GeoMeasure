from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.services.file_service import FileService


def get_file_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileService:
    return FileService(session, settings)


FileServiceDep = Annotated[FileService, Depends(get_file_service)]
