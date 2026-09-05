"""Search: ULPIN pattern, owner, 3D spatial (Section 8)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import Owner, Parcel, Unit, User
from app.schemas.search import (
    OwnerSearchResponse,
    SpatialSearchRequest,
    ULPINSearchResponse,
)
from app.services.geometry_service import box_polyhedral_surface_wkt
from app.services.ulpin_generator import validate_ulpin
from app.utils.geo_utils import model_to_dict

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("/ulpin", response_model=list[ULPINSearchResponse])
def search_ulpin(
    q: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search parcels and units by ULPIN pattern (prefix match)."""
    results: list[ULPINSearchResponse] = []
    units = (
        db.query(Unit).filter(Unit.unit_ulpin.ilike(f"{q}%")).limit(20).all()
    )
    for u in units:
        results.append(
            ULPINSearchResponse(
                ulpin=u.unit_ulpin,
                kind="unit",
                record_id=str(u.unit_id),
                status=u.status.value,
                detail={
                    "building_id": str(u.building_id),
                    "floor_number": u.floor_number,
                    "unit_type": u.unit_type.value,
                },
            )
        )
    unit_ulpins = {u.unit_ulpin for u in units}
    parcels = (
        db.query(Parcel).filter(Parcel.ulpin.ilike(f"{q}%")).limit(20).all()
    )
    for p in parcels:
        if p.ulpin in unit_ulpins:
            continue
        results.append(
            ULPINSearchResponse(
                ulpin=p.ulpin,
                kind="parcel",
                record_id=str(p.parcel_id),
                status=p.status.value,
                detail={"village_code": p.village_code, "parcel_type": p.parcel_type.value},
            )
        )
    return results


@router.get("/owner", response_model=list[OwnerSearchResponse])
def search_owner(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search owners by name; exact match on Aadhaar hash."""
    owners = db.query(Owner).filter(Owner.name.ilike(f"%{q}%")).limit(20).all()
    if not owners and len(q) == 64:
        owners = db.query(Owner).filter(Owner.aadhaar_hash == q).all()
    return [
        OwnerSearchResponse(
            owner_id=str(o.owner_id),
            name=o.name,
            owner_type=o.owner_type.value,
            is_verified=o.is_verified,
            contact=o.contact,
        )
        for o in owners
    ]


@router.post("/spatial")
def spatial_search(
    data: SpatialSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """3D spatial query over unit volumes (point or bbox with z-range)."""
    if data.point:
        lon, lat = float(data.point[0]), float(data.point[1])
        z = float(data.z) if data.z is not None else 0.0
        ewkt = f"SRID=4326;POINT Z ({lon} {lat} {z})"
    elif data.bbox and len(data.bbox) == 4:
        minx, miny, maxx, maxy = (float(v) for v in data.bbox)
        zmin = float(data.z_min) if data.z_min is not None else -50.0
        zmax = float(data.z_max) if data.z_max is not None else 500.0
        box_wkt = box_polyhedral_surface_wkt(minx, miny, maxx, maxy, zmin, zmax)
        ewkt = f"SRID=4326;{box_wkt}"
    else:
        raise HTTPException(status_code=400, detail="Provide point or bbox")

    rows = db.execute(
        text(
            "SELECT unit_id FROM units "
            "WHERE ST_3DIntersects(volume_3d, ST_GeomFromEWKT(:ewkt))"
        ),
        {"ewkt": ewkt},
    ).all()
    unit_ids = [r.unit_id for r in rows]
    if not unit_ids:
        return {"units": [], "count": 0}
    units = db.query(Unit).filter(Unit.unit_id.in_(unit_ids)).all()
    return {
        "units": [model_to_dict(u, ("volume_3d",)) for u in units],
        "count": len(units),
    }


@router.get("/validate-ulpin")
def check_ulpin(
    ulpin: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Checksum validation endpoint (Section 7)."""
    return {"ulpin": ulpin, "valid": validate_ulpin(ulpin)}
