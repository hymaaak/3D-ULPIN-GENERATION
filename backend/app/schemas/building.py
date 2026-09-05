import uuid as uuid_module
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.building import BuildingType


class BuildingCreate(BaseModel):
    parcel_id: uuid_module.UUID
    building_name: str | None = None
    footprint: str | None = None
    height_m: float | None = None
    floors_above_ground: int = 1
    floors_below_ground: int = 0
    construction_year: int | None = None
    building_type: BuildingType = BuildingType.residential
    confidence_score: float | None = None
    metadata: dict | None = None


class BuildingUpdate(BaseModel):
    building_name: str | None = None
    footprint: str | None = None
    height_m: float | None = None
    floors_above_ground: int | None = None
    floors_below_ground: int | None = None
    construction_year: int | None = None
    building_type: BuildingType | None = None
    confidence_score: float | None = None
    metadata: dict | None = None


class BuildingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    building_id: uuid_module.UUID
    parcel_id: uuid_module.UUID
    building_name: str | None = None
    footprint: str | None = None
    height_m: float | None = None
    floors_above_ground: int
    floors_below_ground: int
    construction_year: int | None = None
    building_type: BuildingType
    extracted_by_ml: bool
    confidence_score: float | None = None
    metadata: dict | None = None
    # GeoJSON form of the footprint for map clients (Section: MapViewer fix)
    footprint_geojson: dict | None = None
    created_at: datetime
