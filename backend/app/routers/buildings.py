"""Building CRUD (Section 8)."""
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2 import WKTElement
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_role
from app.models import Building, Parcel, User
from app.schemas.building import (
    BuildingCreate,
    BuildingResponse,
    BuildingUpdate,
)
from app.utils.geo_utils import model_to_dict
from app.utils.validators import is_valid_geometry_wkt

router = APIRouter(prefix="/api/v1/buildings", tags=["buildings"])

GEOM_FIELDS = ("footprint",)


def _to_response(building: Building) -> BuildingResponse:
    data = model_to_dict(building, GEOM_FIELDS)
    fp = data.get("footprint")
    if fp:
        try:
            from geoalchemy2.shape import to_shape
            from shapely import from_wkt

            data["footprint_geojson"] = from_wkt(fp).__geo_interface__
        except Exception:  # noqa: BLE001 — geojson is a convenience, WKT stays canonical
            data["footprint_geojson"] = None
    return BuildingResponse(**data)


@router.get("", response_model=list[BuildingResponse])
def list_buildings(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    parcel_id: uuid_module.UUID | None = None,
    building_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Building)
    if parcel_id:
        query = query.filter(Building.parcel_id == parcel_id)
    if building_type:
        query = query.filter(Building.building_type == building_type)
    return [_to_response(b) for b in query.order_by(Building.created_at).offset(skip).limit(limit).all()]


@router.post("", response_model=BuildingResponse, status_code=status.HTTP_201_CREATED)
def create_building(
    data: BuildingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor", "urban_planner")),
):
    parcel = db.get(Parcel, data.parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    if data.footprint and not is_valid_geometry_wkt(data.footprint):
        raise HTTPException(status_code=400, detail="Invalid footprint WKT")

    footprint = data.footprint
    if not footprint and parcel.geom_2d is not None:
        from geoalchemy2.shape import to_shape

        footprint = to_shape(parcel.geom_2d).wkt

    building = Building(
        parcel_id=data.parcel_id,
        building_name=data.building_name,
        footprint=WKTElement(f"SRID=4326;{footprint}", srid=4326) if footprint else None,
        height_m=data.height_m,
        floors_above_ground=data.floors_above_ground,
        floors_below_ground=data.floors_below_ground,
        construction_year=data.construction_year,
        building_type=data.building_type,
        extracted_by_ml=False,
        confidence_score=data.confidence_score,
        metadata_=data.metadata or {},
    )
    db.add(building)
    db.commit()
    db.refresh(building)
    return _to_response(building)


@router.get("/{building_id}", response_model=BuildingResponse)
def get_building(
    building_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    building = db.get(Building, building_id)
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return _to_response(building)


@router.put("/{building_id}", response_model=BuildingResponse)
def update_building(
    building_id: uuid_module.UUID,
    data: BuildingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor", "urban_planner")),
):
    building = db.get(Building, building_id)
    if building is None:
        raise HTTPException(status_code=404, detail="Building not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "footprint" and value is not None:
            if not is_valid_geometry_wkt(value):
                raise HTTPException(status_code=400, detail="Invalid footprint WKT")
            value = WKTElement(f"SRID=4326;{value}", srid=4326)
        if key == "metadata":
            key = "metadata_"
        setattr(building, key, value)
    db.commit()
    db.refresh(building)
    return _to_response(building)


@router.get("/{building_id}/units")
def list_building_units(
    building_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # volume_3d is a PolyhedralSurfaceZ — GEOS can't parse WKB type 15, so
    # the WKT must come from PostGIS (ST_AsText), not shapely.
    from sqlalchemy import func

    from app.models import Unit

    rows = (
        db.query(Unit, func.ST_AsText(Unit.volume_3d).label("volume_wkt"))
        .filter(Unit.building_id == building_id)
        .all()
    )
    result = []
    for u, volume_wkt in rows:
        data = model_to_dict(u)
        data["volume_3d"] = volume_wkt
        result.append(data)
    return result
