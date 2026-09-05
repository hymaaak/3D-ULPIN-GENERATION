"""File upload to MinIO: multipart upload + presigned URLs (Section 8/15)."""
import uuid as uuid_module

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.dependencies import get_current_user, get_db
from app.models import DataSource, SourceType, User
from app.schemas.data_source import DataSourceResponse
from app.services import file_service

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])
settings = get_settings()


def _detect_source_type(filename: str) -> SourceType:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "tif": SourceType.drone_image,
        "tiff": SourceType.drone_image,
        "laz": SourceType.lidar,
        "las": SourceType.lidar,
        "shp": SourceType.gis_shapefile,
        "geojson": SourceType.gis_shapefile,
        "dwg": SourceType.floor_plan,
        "dxf": SourceType.floor_plan,
        "ifc": SourceType.floor_plan,
        "csv": SourceType.gnss_log,
        "log": SourceType.gnss_log,
        "dem": SourceType.dem,
    }.get(ext, SourceType.survey_sketch)


def _to_response(source: DataSource) -> DataSourceResponse:
    from app.utils.geo_utils import model_to_dict

    return DataSourceResponse(**model_to_dict(source))


@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    file: UploadFile = File(...),
    parcel_id: uuid_module.UUID | None = None,
    source_type: SourceType | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    max_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.UPLOAD_MAX_SIZE_MB} MB limit",
        )
    if size == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    object_name = file_service.make_object_name(file.filename or "upload.bin")
    file_url = file_service.upload_stream(
        file.file,
        object_name,
        size,
        content_type=file.content_type or "application/octet-stream",
    )
    source = DataSource(
        source_type=source_type or _detect_source_type(file.filename or ""),
        file_url=file_url,
        file_size_bytes=size,
        metadata_={"object_name": object_name, "original_filename": file.filename},
        uploaded_by=current_user.user_id,
        parcel_id=parcel_id,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return _to_response(source)


@router.get("/presigned")
def get_presigned_url(
    filename: str = Query(...),
    content_type: str = Query("application/octet-stream"),
    source_type: SourceType | None = Query(None),
    parcel_id: uuid_module.UUID | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Presigned PUT URL for direct-to-MinIO upload (Section 15 flow, step 1-2)."""
    object_name = file_service.make_object_name(filename)
    url = file_service.presigned_put_url(object_name, content_type=content_type)
    source = DataSource(
        source_type=source_type or _detect_source_type(filename),
        file_url=file_service.object_url(object_name),
        metadata_={"object_name": object_name, "original_filename": filename},
        uploaded_by=current_user.user_id,
        parcel_id=parcel_id,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return {
        "source_id": str(source.source_id),
        "upload_url": url,
        "object_name": object_name,
        "file_url": source.file_url,
        "expires_in": 3600,
    }
