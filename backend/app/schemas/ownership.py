import uuid as uuid_module
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.ownership import RightsType


class OwnershipCreate(BaseModel):
    unit_id: uuid_module.UUID
    owner_id: uuid_module.UUID
    rights_type: RightsType = RightsType.full_ownership
    share_percentage: float = 100.0
    valid_from: date
    valid_to: date | None = None
    registration_doc_url: str | None = None


class OwnershipUpdate(BaseModel):
    rights_type: RightsType | None = None
    share_percentage: float | None = None
    valid_to: date | None = None
    registration_doc_url: str | None = None


class OwnershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ownership_id: uuid_module.UUID
    unit_id: uuid_module.UUID
    owner_id: uuid_module.UUID
    rights_type: RightsType
    share_percentage: float
    valid_from: date
    valid_to: date | None = None
    registration_doc_url: str | None = None
    registered_by: uuid_module.UUID | None = None
    created_at: datetime
