from pydantic import BaseModel


class ULPINSearchResponse(BaseModel):
    ulpin: str
    kind: str  # "parcel" | "unit"
    record_id: str
    status: str | None = None
    detail: dict | None = None


class OwnerSearchResponse(BaseModel):
    owner_id: str
    name: str
    owner_type: str
    is_verified: bool
    contact: dict | None = None


class SpatialSearchRequest(BaseModel):
    point: list[float] | None = None
    z: float | None = None
    bbox: list[float] | None = None
    z_min: float | None = None
    z_max: float | None = None
