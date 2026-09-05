import enum
import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ConflictType(str, enum.Enum):
    overlap = "overlap"
    gap = "gap"
    boundary_mismatch = "boundary_mismatch"
    air_right_violation = "air_right_violation"
    utility_intrusion = "utility_intrusion"
    ownership_dispute = "ownership_dispute"


class SeverityLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(str, enum.Enum):
    open = "open"
    under_review = "under_review"
    resolved = "resolved"
    escalated = "escalated"


class ConflictAlert(Base):
    __tablename__ = "conflict_alerts"
    __table_args__ = (
        CheckConstraint("unit_a_id != unit_b_id", name="different_units"),
    )

    alert_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    unit_a_id = Column(
        UUID(as_uuid=True),
        ForeignKey("units.unit_id"),
        nullable=False,
    )
    unit_b_id = Column(
        UUID(as_uuid=True),
        ForeignKey("units.unit_id"),
        nullable=False,
    )
    conflict_type = Column(
        SAEnum(ConflictType, name="conflict_type", native_enum=True, create_type=False),
        nullable=False,
    )
    overlap_volume_cubm = Column(Numeric(12, 4))
    severity = Column(
        SAEnum(SeverityLevel, name="severity_level", native_enum=True, create_type=False),
        nullable=False,
        default=SeverityLevel.medium,
    )
    status = Column(
        SAEnum(AlertStatus, name="alert_status", native_enum=True, create_type=False),
        nullable=False,
        default=AlertStatus.open,
    )
    detected_by_job_id = Column(UUID(as_uuid=True), ForeignKey("processing_jobs.job_id"))
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    resolution_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
