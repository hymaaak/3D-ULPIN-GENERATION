"""Parcel CRUD + 3D/geo queries (Section 8)."""
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2 import Geography, WKTElement
from geoalchemy2.functions import ST_GeomFromText
from sqlalchemy import cast, func
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_role
from app.models import Parcel, ParcelStatus, ParcelType, User
from app.schemas.parcel import (
    GeoSearchRequest,
    ParcelCreate,
    ParcelResponse,
    ParcelUpdate,
)
from app.services.geometry_service import parcel_entities_geojson
from app.services.ulpin_generator import generate_ulpin
from app.utils.geo_utils import deg2_area_to_m2, model_to_dict, safe_from_wkt
from app.utils.validators import is_valid_geometry_wkt

router = APIRouter(prefix="/api/v1/parcels", tags=["parcels"])

GEOM_FIELDS = ("geom_2d", "geom_3d")


def _to_response(parcel: Parcel) -> ParcelResponse:
    return ParcelResponse(**model_to_dict(parcel, GEOM_FIELDS))


def _next_parcel_seq(db: Session, village_code: str) -> int:
    count = (
        db.query(func.count(Parcel.parcel_id))
        .filter(Parcel.village_code == village_code)
        .scalar()
    )
    return int(count or 0) + 1


@router.get("", response_model=list[ParcelResponse])
def list_parcels(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    village_code: str | None = None,
    status: ParcelStatus | None = None,
    parcel_type: ParcelType | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Parcel)
    if village_code:
        query = query.filter(Parcel.village_code == village_code)
    if status:
        query = query.filter(Parcel.status == status)
    if parcel_type:
        query = query.filter(Parcel.parcel_type == parcel_type)
    if q:
        query = query.filter(Parcel.ulpin.ilike(f"%{q}%"))
    return [_to_response(p) for p in query.order_by(Parcel.created_at).offset(skip).limit(limit).all()]


@router.post("", response_model=ParcelResponse, status_code=status.HTTP_201_CREATED)
def create_parcel(
    data: ParcelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor", "urban_planner")),
):
    for geom_field in ("geom_2d", "geom_3d"):
        if not is_valid_geometry_wkt(getattr(data, geom_field)):
            raise HTTPException(status_code=400, detail=f"Invalid {geom_field} WKT")

    village_code = data.village_code or "456789"
    ulpin = data.ulpin or generate_ulpin(
        "27", "023", village_code, _next_parcel_seq(db, village_code), 0, 0
    )

    area_sqm = data.area_sqm
    if area_sqm is None and data.geom_2d:
        geom = safe_from_wkt(data.geom_2d)
        if geom is not None:
            _, miny, _, maxy = geom.bounds
            area_sqm = round(deg2_area_to_m2(geom.area, (miny + maxy) / 2.0), 2)

    parcel = Parcel(
        ulpin=ulpin,
        legacy_survey_no=data.legacy_survey_no,
        village_code=village_code,
        geom_2d=WKTElement(f"SRID=4326;{data.geom_2d}", srid=4326) if data.geom_2d else None,
        geom_3d=WKTElement(f"SRID=4326;{data.geom_3d}", srid=4326, extended=True)
        if data.geom_3d
        else None,
        area_sqm=area_sqm,
        parcel_type=data.parcel_type,
        status=data.status,
        metadata_=data.metadata or {},
        created_by=current_user.user_id,
    )
    db.add(parcel)
    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create parcel: {exc}")
    db.refresh(parcel)
    return _to_response(parcel)


@router.post("/search", response_model=list[ParcelResponse])
def geo_search(
    data: GeoSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Parcel)
    if data.bbox and len(data.bbox) == 4:
        minx, miny, maxx, maxy = data.bbox
        envelope = ST_GeomFromText(
            f"POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, "
            f"{minx} {maxy}, {minx} {miny}))",
            4326,
        )
        query = query.filter(func.ST_Intersects(Parcel.geom_2d, envelope))
    elif data.radius:
        lon = float(data.radius.get("lon"))
        lat = float(data.radius.get("lat"))
        r_m = float(data.radius.get("r_m", 100))
        point = func.ST_GeogFromText(f"POINT({lon} {lat})")
        query = query.filter(
            func.ST_DWithin(cast(Parcel.geom_2d, Geography), point, r_m)
        )
    elif data.polygon:
        coords = ", ".join(f"{c[0]} {c[1]}" for c in data.polygon)
        poly = ST_GeomFromText(f"POLYGON(({coords}))", 4326)
        query = query.filter(func.ST_Intersects(Parcel.geom_2d, poly))
    else:
        raise HTTPException(
            status_code=400, detail="Provide bbox, radius or polygon"
        )
    if data.village_code:
        query = query.filter(Parcel.village_code == data.village_code)
    if data.status:
        query = query.filter(Parcel.status == data.status)
    return [_to_response(p) for p in query.all()]


@router.get("/{parcel_id}", response_model=ParcelResponse)
def get_parcel(
    parcel_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return _to_response(parcel)


@router.put("/{parcel_id}", response_model=ParcelResponse)
def update_parcel(
    parcel_id: uuid_module.UUID,
    data: ParcelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor", "urban_planner")),
):
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in GEOM_FIELDS and value is not None:
            if not is_valid_geometry_wkt(value):
                raise HTTPException(status_code=400, detail=f"Invalid {key} WKT")
            value = WKTElement(f"SRID=4326;{value}", srid=4326, extended=key == "geom_3d")
        if key == "metadata":
            key = "metadata_"
        setattr(parcel, key, value)
    db.commit()
    db.refresh(parcel)
    return _to_response(parcel)


@router.delete("/{parcel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_parcel(
    parcel_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    db.delete(parcel)
    db.commit()
    return None


@router.get("/{parcel_id}/buildings")
def list_parcel_buildings(
    parcel_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models import Building

    buildings = (
        db.query(Building).filter(Building.parcel_id == parcel_id).all()
    )
    return [
        model_to_dict(b, ("footprint",))
        for b in buildings
    ]


@router.get("/{parcel_id}/3d-tiles")
def parcel_3d_tiles(
    parcel_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Demo 3D tile endpoint: returns Cesium-ready GeoJSON entities."""
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return parcel_entities_geojson(db, parcel_id)
