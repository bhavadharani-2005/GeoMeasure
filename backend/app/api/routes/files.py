import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, Query, Response, UploadFile, status

from app.api.deps import FileServiceDep
from app.core.config import Settings, get_settings
from app.core.exceptions import FileTooLargeError, InvalidFileTypeError
from app.schemas.feature import GeoJsonFeatureCollection, MeasurementsResponse
from app.schemas.file import FileDetail, FileSummary, FileUploadResponse

router = APIRouter(prefix="/api/files", tags=["files"])

MULTIPART_OVERHEAD_BYTES = 1024 * 1024
ERROR_RESPONSES = {
    400: {"description": "Unsupported or empty upload"},
    404: {"description": "File not found"},
    413: {"description": "File too large"},
    422: {"description": "File could not be processed"},
}


@router.post(
    "/",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
    summary="Upload and process a KML file or zipped Shapefile",
)
def upload_file(
    service: FileServiceDep,
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(description="A .kml file or a .zip containing a Shapefile")],
    content_length: Annotated[int | None, Header()] = None,
):
    # Reject obviously oversized bodies early; the streamed size check is authoritative.
    if content_length and content_length > settings.max_upload_bytes + MULTIPART_OVERHEAD_BYTES:
        raise FileTooLargeError(f"The file exceeds the {settings.max_upload_mb} MB upload limit.")
    if not file.filename:
        raise InvalidFileTypeError()
    return service.upload(file.filename, file.file)


@router.get("/", response_model=list[FileSummary], summary="List uploaded files, newest first")
def list_files(
    service: FileServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return service.list_files(limit, offset)


@router.get(
    "/{file_id}/",
    response_model=FileDetail,
    responses=ERROR_RESPONSES,
    summary="Get file metadata",
)
def get_file(file_id: uuid.UUID, service: FileServiceDep):
    return service.get_detail(file_id)


@router.get(
    "/{file_id}/measurements/",
    response_model=MeasurementsResponse,
    responses={**ERROR_RESPONSES, 409: {"description": "File was not processed successfully"}},
    summary="Get features and their measurements",
)
def get_measurements(file_id: uuid.UUID, service: FileServiceDep):
    return service.measurements(file_id)


@router.get(
    "/{file_id}/geojson/",
    response_model=GeoJsonFeatureCollection,
    responses=ERROR_RESPONSES,
    summary="Get features as GeoJSON (EPSG:4326) for mapping",
)
def get_geojson(file_id: uuid.UUID, service: FileServiceDep):
    return service.geojson(file_id)


@router.delete(
    "/{file_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=ERROR_RESPONSES,
    summary="Delete a file, its features, and the stored upload",
)
def delete_file(file_id: uuid.UUID, service: FileServiceDep) -> Response:
    service.delete(file_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
