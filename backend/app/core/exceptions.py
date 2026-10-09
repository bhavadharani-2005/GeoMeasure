import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for all errors that are safe to show to API clients."""

    status_code = 500
    code = "INTERNAL_ERROR"
    message = "Something went wrong."

    def __init__(self, message: str | None = None, **details: Any) -> None:
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)


class InvalidFileTypeError(AppError):
    status_code = 400
    code = "INVALID_FILE_TYPE"
    message = "Only .kml and zipped Shapefiles (.zip) are supported."


class EmptyFileError(AppError):
    status_code = 400
    code = "EMPTY_FILE"
    message = "The uploaded file is empty."


class FileTooLargeError(AppError):
    status_code = 413
    code = "FILE_TOO_LARGE"
    message = "The uploaded file exceeds the maximum allowed size."


class InvalidArchiveError(AppError):
    status_code = 422
    code = "INVALID_ZIP"
    message = "The uploaded file is not a valid ZIP archive."


class InvalidShapefileError(AppError):
    status_code = 422
    code = "INVALID_SHAPEFILE"
    message = "The ZIP archive does not contain a valid Shapefile."


class UnreadableFileError(AppError):
    status_code = 422
    code = "UNREADABLE_FILE"
    message = "The file could not be read as geospatial data."


class MissingCrsError(AppError):
    status_code = 422
    code = "MISSING_CRS"
    message = (
        "The dataset has no coordinate reference system, so measurements cannot be "
        "calculated safely. For Shapefiles, include the .prj file."
    )


class EmptyDatasetError(AppError):
    status_code = 422
    code = "EMPTY_DATASET"
    message = "The file contains no features with usable geometry."


class TooManyFeaturesError(AppError):
    status_code = 422
    code = "TOO_MANY_FEATURES"
    message = "The dataset contains more features than this service processes."


class ProcessingError(AppError):
    status_code = 500
    code = "PROCESSING_FAILED"
    message = "Processing failed unexpectedly. The error has been logged."


class FileNotFoundInDbError(AppError):
    status_code = 404
    code = "FILE_NOT_FOUND"
    message = "No file exists with that id."


class FileNotReadyError(AppError):
    status_code = 409
    code = "FILE_NOT_PROCESSED"
    message = "This file has not been processed successfully."


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"error": error}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first["loc"] if part != "body")
        message = f"Invalid request: {location}: {first['msg']}" if location else first["msg"]
        return JSONResponse(status_code=422, content=_error_body("VALIDATION_ERROR", message))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code, content=_error_body(code, str(exc.detail))
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500, content=_error_body("INTERNAL_ERROR", AppError.message)
        )
