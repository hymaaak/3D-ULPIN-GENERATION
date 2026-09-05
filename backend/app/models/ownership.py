import enum
import uuid

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class RightsType(str, enum.Enum):
    full_ownership = "full_ownership"
    lease = "lease"
    easement = "easement"
    air_right = "air_right"
    subsurface = "subsurface"
    joint = "joint"


class OwnershipRecord(Base):
    __tablename__ = "ownership_records"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="valid_date_range",
        ),
    )

    ownership_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("units.unit_id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("owners.owner_id"),
        nullable=False,
    )
    rights_type = Column(
        SAEnum(RightsType, name="rights_type", native_enum=True, create_type=False),
        nullable=False,
        default=RightsType.full_ownership,
    )
    share_percentage = Column(Numeric(5, 2), nullable=False, default=100.00)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date)
    registration_doc_url = Column(Text)
    registered_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
