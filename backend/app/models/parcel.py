import enum
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from geoalchemy2 import Geometry

from app.database import Base


class ParcelType(str, enum.Enum):
    surface = "surface"
    multi_storey = "multi_storey"
    underground = "underground"
    air_right = "air_right"
    mixed = "mixed"


class ParcelStatus(str, enum.Enum):
    draft = "draft"
    verified = "verified"
    disputed = "disputed"
    archived = "archived"


class Parcel(Base):
    __tablename__ = "parcels"

    parcel_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    ulpin = Column(String(50), unique=True, nullable=False)
    legacy_survey_no = Column(String(50))
    village_code = Column(String(10))
    geom_2d = Column(Geometry(geometry_type="POLYGON", srid=4326))
    geom_3d = Column(Geometry(geometry_type="POLYHEDRALSURFACEZ", srid=4326))
    area_sqm = Column(Numeric(12, 2))
    parcel_type = Column(
        SAEnum(ParcelType, name="parcel_type", native_enum=True, create_type=False),
        nullable=False,
        default=ParcelType.surface,
    )
    status = Column(
        SAEnum(ParcelStatus, name="parcel_status", native_enum=True, create_type=False),
        nullable=False,
        default=ParcelStatus.draft,
    )
    metadata_ = Column("metadata", JSONB, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
