import enum
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from geoalchemy2 import Geometry

from app.database import Base
from app.models.parcel import ParcelStatus


class UnitType(str, enum.Enum):
    apartment = "apartment"
    shop = "shop"
    office = "office"
    parking = "parking"
    storage = "storage"
    utility = "utility"
    air_right = "air_right"
    pipeline = "pipeline"
    tunnel = "tunnel"


class Unit(Base):
    __tablename__ = "units"

    unit_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    building_id = Column(
        UUID(as_uuid=True),
        ForeignKey("buildings.building_id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.parcel_id"))
    unit_ulpin = Column(String(50), unique=True, nullable=False)
    volume_3d = Column(
        Geometry(geometry_type="POLYHEDRALSURFACEZ", srid=4326),
        nullable=False,
    )
    floor_number = Column(Integer)
    floor_label = Column(String(20))
    unit_type = Column(
        SAEnum(UnitType, name="unit_type", native_enum=True, create_type=False),
        nullable=False,
        default=UnitType.apartment,
    )
    area_sqm = Column(Numeric(10, 2))
    volume_cubm = Column(Numeric(12, 2))
    height_min_m = Column(Numeric(8, 2))
    height_max_m = Column(Numeric(8, 2))
    status = Column(
        SAEnum(ParcelStatus, name="parcel_status", native_enum=True, create_type=False),
        nullable=False,
        default=ParcelStatus.draft,
    )
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
