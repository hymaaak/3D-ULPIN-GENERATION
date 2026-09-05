"""Ownership record CRUD + temporal history (Section 8)."""
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_role
from app.models import Owner, OwnershipRecord, Unit, User
from app.schemas.ownership import (
    OwnershipCreate,
    OwnershipResponse,
    OwnershipUpdate,
)
from app.utils.geo_utils import model_to_dict
from app.utils.validators import is_valid_date_range

router = APIRouter(prefix="/api/v1/ownership", tags=["ownership"])


def _to_response(record: OwnershipRecord) -> OwnershipResponse:
    return OwnershipResponse(**model_to_dict(record))


@router.get("", response_model=list[OwnershipResponse])
def list_ownership(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    unit_id: uuid_module.UUID | None = None,
    owner_id: uuid_module.UUID | None = None,
    rights_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(OwnershipRecord)
    if unit_id:
        query = query.filter(OwnershipRecord.unit_id == unit_id)
    if owner_id:
        query = query.filter(OwnershipRecord.owner_id == owner_id)
    if rights_type:
        query = query.filter(OwnershipRecord.rights_type == rights_type)
    return [
        _to_response(r)
        for r in query.order_by(OwnershipRecord.created_at).offset(skip).limit(limit).all()
    ]


@router.post("", response_model=OwnershipResponse, status_code=status.HTTP_201_CREATED)
def create_ownership(
    data: OwnershipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor", "urban_planner")),
):
    if db.get(Unit, data.unit_id) is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    if db.get(Owner, data.owner_id) is None:
        raise HTTPException(status_code=404, detail="Owner not found")
    if not is_valid_date_range(data.valid_from, data.valid_to):
        raise HTTPException(
            status_code=400, detail="valid_to must be after valid_from"
        )
    record = OwnershipRecord(
        unit_id=data.unit_id,
        owner_id=data.owner_id,
        rights_type=data.rights_type,
        share_percentage=data.share_percentage,
        valid_from=data.valid_from,
        valid_to=data.valid_to,
        registration_doc_url=data.registration_doc_url,
        registered_by=current_user.user_id,
    )
    db.add(record)
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create record: {exc}")
    db.refresh(record)
    return _to_response(record)


@router.get("/history/{unit_id}")
def ownership_history(
    unit_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full temporal ownership history for a unit."""
    records = (
        db.query(OwnershipRecord)
        .filter(OwnershipRecord.unit_id == unit_id)
        .order_by(OwnershipRecord.valid_from.asc())
        .all()
    )
    return [model_to_dict(r) for r in records]


@router.get("/{ownership_id}", response_model=OwnershipResponse)
def get_ownership(
    ownership_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.get(OwnershipRecord, ownership_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Ownership record not found")
    return _to_response(record)


@router.put("/{ownership_id}", response_model=OwnershipResponse)
def update_ownership(
    ownership_id: uuid_module.UUID,
    data: OwnershipUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor", "urban_planner")),
):
    record = db.get(OwnershipRecord, ownership_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Ownership record not found")
    update_data = data.model_dump(exclude_unset=True)
    if "valid_to" in update_data and not is_valid_date_range(
        record.valid_from, update_data["valid_to"]
    ):
        raise HTTPException(status_code=400, detail="valid_to must be after valid_from")
    for key, value in update_data.items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return _to_response(record)


@router.delete("/{ownership_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ownership(
    ownership_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    record = db.get(OwnershipRecord, ownership_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Ownership record not found")
    db.delete(record)
    db.commit()
    return None
