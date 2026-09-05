import enum
import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class OwnerType(str, enum.Enum):
    individual = "individual"
    government = "government"
    corporation = "corporation"
    trust = "trust"
    religious = "religious"


class Owner(Base):
    __tablename__ = "owners"

    owner_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    owner_type = Column(
        SAEnum(OwnerType, name="owner_type", native_enum=True, create_type=False),
        nullable=False,
        default=OwnerType.individual,
    )
    name = Column(String(255), nullable=False)
    name_local = Column(String(255))
    aadhaar_hash = Column(String(64), unique=True)
    pan_hash = Column(String(64))
    contact = Column(JSONB, default=dict)
    guardian_name = Column(String(255))
    date_of_birth = Column(Date)
    is_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
