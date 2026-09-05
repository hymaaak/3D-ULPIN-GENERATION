import uuid as uuid_module
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.parcel import ParcelStatus, ParcelType


class ParcelCreate(BaseModel):
    ulpin: str | None = None
    legacy_survey_no: str | None = None
    village_code: str | None = None
    geom_2d: str | None = None
    geom_3d: str | None = None
    area_sqm: float | None = None
    parcel_type: ParcelType = ParcelType.surface
    status: ParcelStatus = ParcelStatus.draft
    metadata: dict | None = None


class ParcelUpdate(BaseModel):
    legacy_survey_no: str | None = None
    village_code: str | None = None
    geom_2d: str | None = None
    geom_3d: str | None = None
    area_sqm: float | None = None
    parcel_type: ParcelType | None = None
    status: ParcelStatus | None = None
    metadata: dict | None = None


class ParcelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parcel_id: uuid_module.UUID
    ulpin: str
    legacy_survey_no: str | None = None
    village_code: str | None = None
    geom_2d: str | None = None
    geom_3d: str | None = None
    area_sqm: float | None = None
    parcel_type: ParcelType
    status: ParcelStatus
    metadata: dict | None = None
    created_by: uuid_module.UUID | None = None
    created_at: datetime
    updated_at: datetime


class GeoSearchRequest(BaseModel):
    bbox: list[float] | None = None
    radius: dict | None = None
    polygon: list[list[float]] | None = None
    village_code: str | None = None
    status: ParcelStatus | None = None
