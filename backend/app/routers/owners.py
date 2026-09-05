"""Owner management CRUD (Section 8)."""
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_role
from app.models import Owner, User
from app.schemas.owner import OwnerCreate, OwnerResponse, OwnerUpdate
from app.utils.geo_utils import model_to_dict

router = APIRouter(prefix="/api/v1/owners", tags=["owners"])


def _to_response(owner: Owner) -> OwnerResponse:
    return OwnerResponse(**model_to_dict(owner))


@router.get("", response_model=list[OwnerResponse])
def list_owners(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    owner_type: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Owner)
    if owner_type:
        query = query.filter(Owner.owner_type == owner_type)
    if q:
        query = query.filter(Owner.name.ilike(f"%{q}%"))
    return [_to_response(o) for o in query.order_by(Owner.created_at).offset(skip).limit(limit).all()]


@router.post("", response_model=OwnerResponse, status_code=status.HTTP_201_CREATED)
def create_owner(
    data: OwnerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor", "urban_planner")),
):
    owner = Owner(
        owner_type=data.owner_type,
        name=data.name,
        name_local=data.name_local,
        aadhaar_hash=data.aadhaar_hash,
        pan_hash=data.pan_hash,
        contact=data.contact or {},
        guardian_name=data.guardian_name,
        date_of_birth=data.date_of_birth,
        is_verified=data.is_verified,
    )
    db.add(owner)
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create owner: {exc}")
    db.refresh(owner)
    return _to_response(owner)


@router.get("/{owner_id}", response_model=OwnerResponse)
def get_owner(
    owner_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    owner = db.get(Owner, owner_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Owner not found")
    return _to_response(owner)


@router.put("/{owner_id}", response_model=OwnerResponse)
def update_owner(
    owner_id: uuid_module.UUID,
    data: OwnerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor", "urban_planner")),
):
    owner = db.get(Owner, owner_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Owner not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(owner, key, value)
    db.commit()
    db.refresh(owner)
    return _to_response(owner)


@router.get("/{owner_id}/units")
def owner_units(
    owner_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Units currently linked to an owner via ownership records."""
    from app.models import OwnershipRecord, Unit

    records = db.query(OwnershipRecord).filter(OwnershipRecord.owner_id == owner_id).all()
    unit_ids = [r.unit_id for r in records]
    if not unit_ids:
        return []
    units = db.query(Unit).filter(Unit.unit_id.in_(unit_ids)).all()
    return [model_to_dict(u, ("volume_3d",)) for u in units]
