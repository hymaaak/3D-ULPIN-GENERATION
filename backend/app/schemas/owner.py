import uuid as uuid_module
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.owner import OwnerType


class OwnerCreate(BaseModel):
    owner_type: OwnerType = OwnerType.individual
    name: str
    name_local: str | None = None
    aadhaar_hash: str | None = None
    pan_hash: str | None = None
    contact: dict | None = None
    guardian_name: str | None = None
    date_of_birth: date | None = None
    is_verified: bool = False


class OwnerUpdate(BaseModel):
    owner_type: OwnerType | None = None
    name: str | None = None
    name_local: str | None = None
    pan_hash: str | None = None
    contact: dict | None = None
    guardian_name: str | None = None
    date_of_birth: date | None = None
    is_verified: bool | None = None


class OwnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    owner_id: uuid_module.UUID
    owner_type: OwnerType
    name: str
    name_local: str | None = None
    aadhaar_hash: str | None = None
    pan_hash: str | None = None
    contact: dict | None = None
    guardian_name: str | None = None
    date_of_birth: date | None = None
    is_verified: bool
    created_at: datetime
