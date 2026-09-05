import uuid as uuid_module
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.data_source import ProcessingStatus, SourceType


class DataSourceCreate(BaseModel):
    source_type: SourceType
    file_url: str
    file_size_bytes: int | None = None
    metadata: dict | None = None
    parcel_id: uuid_module.UUID | None = None


class DataSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: uuid_module.UUID
    source_type: SourceType
    file_url: str
    file_size_bytes: int | None = None
    metadata: dict | None = None
    uploaded_by: uuid_module.UUID | None = None
    parcel_id: uuid_module.UUID | None = None
    processing_status: ProcessingStatus
    created_at: datetime
