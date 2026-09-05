"""Spatial conflict detection via the PostGIS detect_3d_conflicts() function."""
from __future__ import annotations

import uuid as uuid_module

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    AlertStatus,
    ConflictAlert,
    ConflictType,
    SeverityLevel,
    Unit,
)

_CONFLICT_TYPE_MAP = {ctype.value: ctype for ctype in ConflictType}
_OPEN_STATUSES = [AlertStatus.open, AlertStatus.under_review, AlertStatus.escalated]


def _severity_for_volume(volume: float | None) -> SeverityLevel:
    if volume is None:
        return SeverityLevel.medium
    if volume > 50:
        return SeverityLevel.critical
    if volume > 10:
        return SeverityLevel.high
    if volume > 1:
        return SeverityLevel.medium
    return SeverityLevel.low


def detect_conflicts_for_unit(
    db: Session,
    unit_id,
    job_id=None,
) -> list[ConflictAlert]:
    """Run detect_3d_conflicts(p_unit_id) and persist new conflict_alerts rows."""
    rows = db.execute(
        text(
            "SELECT conflicting_unit_id, conflict_type, overlap_volume "
            "FROM detect_3d_conflicts(:uid)"
        ),
        {"uid": str(unit_id)},
    ).all()

    alerts: list[ConflictAlert] = []
    for conflicting_unit_id, conflict_type, overlap_volume in rows:
        pair_exists = (
            db.query(ConflictAlert)
            .filter(
                ConflictAlert.unit_a_id == unit_id,
                ConflictAlert.unit_b_id == conflicting_unit_id,
                ConflictAlert.status.in_(_OPEN_STATUSES),
            )
            .first()
        )
        if pair_exists:
            continue
        alert = ConflictAlert(
            alert_id=uuid_module.uuid4(),
            unit_a_id=unit_id,
            unit_b_id=conflicting_unit_id,
            conflict_type=_CONFLICT_TYPE_MAP.get(conflict_type, ConflictType.overlap),
            overlap_volume_cubm=overlap_volume,
            severity=_severity_for_volume(float(overlap_volume) if overlap_volume else None),
            detected_by_job_id=job_id,
        )
        db.add(alert)
        alerts.append(alert)
    db.commit()
    return alerts


def detect_conflicts_for_parcel(db: Session, parcel_id, job_id=None) -> list[ConflictAlert]:
    units = db.query(Unit).filter(Unit.parent_parcel_id == parcel_id).all()
    alerts: list[ConflictAlert] = []
    for unit in units:
        alerts.extend(detect_conflicts_for_unit(db, unit.unit_id, job_id=job_id))
    return alerts
