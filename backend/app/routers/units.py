"""Unit (3D volume) CRUD + ULPIN lookup (Section 8)."""
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2 import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_role
from app.models import Building, OwnershipRecord, Parcel, Unit, User
from app.schemas.unit import UnitCreate, UnitResponse, UnitUpdate
from app.services.geometry_service import extrude_footprint
from app.services.ulpin_generator import generate_ulpin, parse_ulpin
from app.utils.geo_utils import model_to_dict
from app.utils.validators import is_valid_geometry_wkt

router = APIRouter(prefix="/api/v1/units", tags=["units"])

GEOM_FIELDS = ("volume_3d",)


def _to_response(unit: Unit) -> UnitResponse:
    return UnitResponse(**model_to_dict(unit, GEOM_FIELDS))


def _parcel_codes(db: Session, parcel_id) -> tuple[str, str, str, int]:
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        return "27", "023", "456789", 1
    parsed = parse_ulpin(parcel.ulpin)
    if parsed:
        return (
            str(parsed["state"]),
            str(parsed["district"]),
            str(parsed["village"]),
            int(parsed["parcel"]),
        )
    return "27", "023", parcel.village_code or "456789", 1


@router.get("", response_model=list[UnitResponse])
def list_units(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    building_id: uuid_module.UUID | None = None,
    floor_number: int | None = None,
    unit_type: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Unit)
    if building_id:
        query = query.filter(Unit.building_id == building_id)
    if floor_number is not None:
        query = query.filter(Unit.floor_number == floor_number)
    if unit_type:
        query = query.filter(Unit.unit_type == unit_type)
    if status:
        query = query.filter(Unit.status == status)
    return [
        _to_response(u)
        for u in query.order_by(Unit.created_at).offset(skip).limit(limit).all()
    ]


@router.post("", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
def create_unit(
    data: UnitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor", "urban_planner")),
):
    building = db.get(Building, data.building_id)
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")

    if data.footprint_2d:
        if not is_valid_geometry_wkt(data.footprint_2d):
            raise HTTPException(status_code=400, detail="Invalid footprint_2d WKT")
        footprint_wkt = data.footprint_2d
    elif building.footprint is not None:
        footprint_wkt = to_shape(building.footprint).wkt
    else:
        raise HTTPException(
            status_code=400,
            detail="Unit needs a footprint: provide footprint_2d or set the building footprint",
        )

    # Default to a standard 3 m storey for the requested floor
    floor_height = 3.0
    zmin = data.height_min_m if data.height_min_m is not None else (data.floor_number - 1) * floor_height
    zmax = data.height_max_m if data.height_max_m is not None else data.floor_number * floor_height

    volume_wkt, area_sqm, volume_cubm = extrude_footprint(footprint_wkt, zmin, zmax)
    state, district, village, parcel_seq = _parcel_codes(db, building.parcel_id)
    unit_ulpin = generate_ulpin(
        state, district, village, parcel_seq, data.floor_number, data.unit_number
    )

    unit = Unit(
        building_id=data.building_id,
        parent_parcel_id=building.parcel_id,
        unit_ulpin=unit_ulpin,
        volume_3d=WKTElement(f"SRID=4326;{volume_wkt}", srid=4326, extended=True),
        floor_number=data.floor_number,
        floor_label=data.floor_label or f"F{data.floor_number:02d}",
        unit_type=data.unit_type,
        area_sqm=area_sqm,
        volume_cubm=volume_cubm,
        height_min_m=zmin,
        height_max_m=zmax,
        status=data.status,
        metadata_={"unit_index": data.unit_number, **(data.metadata or {})},
    )
    db.add(unit)
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create unit: {exc}")
    db.refresh(unit)
    return _to_response(unit)


@router.get("/ulpin/{ulpin}", response_model=UnitResponse)
def get_unit_by_ulpin(
    ulpin: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    unit = db.query(Unit).filter(Unit.unit_ulpin == ulpin).first()
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found for ULPIN")
    return _to_response(unit)


@router.get("/{unit_id}", response_model=UnitResponse)
def get_unit(
    unit_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    unit = db.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    return _to_response(unit)


@router.put("/{unit_id}", response_model=UnitResponse)
def update_unit(
    unit_id: uuid_module.UUID,
    data: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor", "urban_planner")),
):
    unit = db.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "volume_3d" and value is not None:
            value = WKTElement(f"SRID=4326;{value}", srid=4326, extended=True)
        if key == "metadata":
            key = "metadata_"
        setattr(unit, key, value)
    db.commit()
    db.refresh(unit)
    return _to_response(unit)


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit(
    unit_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor")),
):
    unit = db.get(Unit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    db.delete(unit)
    db.commit()
    return None


@router.get("/{unit_id}/ownership")
def unit_ownership(
    unit_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = (
        db.query(OwnershipRecord)
        .filter(OwnershipRecord.unit_id == unit_id)
        .order_by(OwnershipRecord.valid_from.desc())
        .all()
    )
    return [model_to_dict(r) for r in records]


@router.get("/{unit_id}/volume-bbox")
def unit_volume_bbox(
    unit_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """3D bounds of a unit volume via PostGIS ST_3DExtent."""
    from sqlalchemy import text

    row = db.execute(
        text(
            "SELECT ST_3DExtent(volume_3d) AS extent FROM units WHERE unit_id = :uid"
        ),
        {"uid": str(unit_id)},
    ).first()
    if row is None or row.extent is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    return {"unit_id": str(unit_id), "extent_3d": row.extent}
