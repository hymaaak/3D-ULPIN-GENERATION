import uuid as uuid_module
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.conflict_alert import AlertStatus, ConflictType, SeverityLevel


class ConflictResolveRequest(BaseModel):
    resolution_notes: str | None = None
    status: AlertStatus = AlertStatus.resolved


class ConflictDetectRequest(BaseModel):
    unit_id: uuid_module.UUID | None = None
    parcel_id: uuid_module.UUID | None = None


class ConflictAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    alert_id: uuid_module.UUID
    unit_a_id: uuid_module.UUID
    unit_b_id: uuid_module.UUID
    conflict_type: ConflictType
    overlap_volume_cubm: float | None = None
    severity: SeverityLevel
    status: AlertStatus
    detected_by_job_id: uuid_module.UUID | None = None
    assigned_to: uuid_module.UUID | None = None
    resolution_notes: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
