"""3D tile endpoints (demo mode: Cesium-ready GeoJSON entities)."""
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import Parcel, User
from app.services.geometry_service import parcel_entities_geojson

router = APIRouter(prefix="/api/v1/tiles", tags=["tiles"])


@router.get("/parcel/{parcel_id}/entities")
def parcel_entities(
    parcel_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Demo 3D payload: GeoJSON FeatureCollection with extrusion properties."""
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return parcel_entities_geojson(db, parcel_id)


@router.get("/{z}/{x}/{y}.mvt")
def mock_vector_tile(
    z: int,
    x: int,
    y: int,
    current_user: User = Depends(get_current_user),
):
    """Placeholder vector tile endpoint — empty 204 for the demo viewer."""
    return Response(status_code=204)
