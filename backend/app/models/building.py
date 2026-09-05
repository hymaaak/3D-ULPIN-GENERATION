import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from geoalchemy2 import Geometry

from app.database import Base


class BuildingType(str, enum.Enum):
    residential = "residential"
    commercial = "commercial"
    industrial = "industrial"
    mixed = "mixed"
    infrastructure = "infrastructure"


class Building(Base):
    __tablename__ = "buildings"

    building_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    parcel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parcels.parcel_id", ondelete="CASCADE"),
        nullable=False,
    )
    building_name = Column(String(200))
    footprint = Column(Geometry(geometry_type="POLYGON", srid=4326))
    height_m = Column(Numeric(8, 2))
    floors_above_ground = Column(Integer, nullable=False, default=1)
    floors_below_ground = Column(Integer, nullable=False, default=0)
    construction_year = Column(Integer)
    building_type = Column(
        SAEnum(BuildingType, name="building_type", native_enum=True, create_type=False),
        nullable=False,
        default=BuildingType.residential,
    )
    extracted_by_ml = Column(Boolean, nullable=False, default=False)
    confidence_score = Column(Numeric(3, 2))
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
