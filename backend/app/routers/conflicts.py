"""Conflict alerts: list, detail, resolve, run detection (Section 8)."""
import datetime as dt
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_role
from app.models import (
    AlertStatus,
    ConflictAlert,
    SeverityLevel,
    User,
)
from app.schemas.conflict_alert import (
    ConflictAlertResponse,
    ConflictDetectRequest,
    ConflictResolveRequest,
)
from app.services.conflict_service import (
    detect_conflicts_for_parcel,
    detect_conflicts_for_unit,
)
from app.utils.geo_utils import model_to_dict

router = APIRouter(prefix="/api/v1/conflicts", tags=["conflicts"])


def _to_response(alert: ConflictAlert) -> ConflictAlertResponse:
    return ConflictAlertResponse(**model_to_dict(alert))


@router.get("", response_model=list[ConflictAlertResponse])
def list_conflicts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    severity: SeverityLevel | None = None,
    status: AlertStatus | None = None,
    conflict_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ConflictAlert)
    if severity:
        query = query.filter(ConflictAlert.severity == severity)
    if status:
        query = query.filter(ConflictAlert.status == status)
    if conflict_type:
        query = query.filter(ConflictAlert.conflict_type == conflict_type)
    return [
        _to_response(a)
        for a in query.order_by(ConflictAlert.created_at.desc()).offset(skip).limit(limit).all()
    ]


@router.post("/detect")
def detect_conflicts(
    data: ConflictDetectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor", "validator")),
):
    """Run 3D conflict detection on a unit or all units of a parcel."""
    if data.unit_id is None and data.parcel_id is None:
        raise HTTPException(status_code=400, detail="Provide unit_id or parcel_id")
    if data.unit_id is not None:
        alerts = detect_conflicts_for_unit(db, data.unit_id)
    else:
        alerts = detect_conflicts_for_parcel(db, data.parcel_id)
    return {"conflicts_detected": len(alerts), "alerts": [_to_response(a) for a in alerts]}


@router.get("/{alert_id}", response_model=ConflictAlertResponse)
def get_conflict(
    alert_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alert = db.get(ConflictAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Conflict alert not found")
    return _to_response(alert)


@router.put("/{alert_id}/resolve", response_model=ConflictAlertResponse)
def resolve_conflict(
    alert_id: uuid_module.UUID,
    data: ConflictResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor", "validator")),
):
    alert = db.get(ConflictAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Conflict alert not found")
    alert.status = data.status
    alert.resolution_notes = data.resolution_notes
    alert.assigned_to = current_user.user_id
    if data.status == AlertStatus.resolved:
        alert.resolved_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    db.refresh(alert)
    return _to_response(alert)
