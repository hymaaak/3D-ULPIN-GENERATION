import uuid as uuid_module
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.parcel import ParcelStatus
from app.models.unit import UnitType


class UnitCreate(BaseModel):
    building_id: uuid_module.UUID
    floor_number: int = 1
    floor_label: str | None = None
    unit_number: int = 1
    unit_type: UnitType = UnitType.apartment
    footprint_2d: str | None = None
    height_min_m: float | None = None
    height_max_m: float | None = None
    status: ParcelStatus = ParcelStatus.draft
    metadata: dict | None = None


class UnitUpdate(BaseModel):
    floor_number: int | None = None
    floor_label: str | None = None
    unit_type: UnitType | None = None
    volume_3d: str | None = None
    area_sqm: float | None = None
    volume_cubm: float | None = None
    height_min_m: float | None = None
    height_max_m: float | None = None
    status: ParcelStatus | None = None
    metadata: dict | None = None


class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unit_id: uuid_module.UUID
    building_id: uuid_module.UUID
    parent_parcel_id: uuid_module.UUID | None = None
    unit_ulpin: str
    volume_3d: str | None = None
    floor_number: int | None = None
    floor_label: str | None = None
    unit_type: UnitType
    area_sqm: float | None = None
    volume_cubm: float | None = None
    height_min_m: float | None = None
    height_max_m: float | None = None
    status: ParcelStatus
    metadata: dict | None = None
    created_at: datetime
