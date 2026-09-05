import enum
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class JobType(str, enum.Enum):
    building_extraction = "building_extraction"
    floor_segmentation = "floor_segmentation"
    vertical_delineation = "vertical_delineation"
    topology_validation = "topology_validation"
    ulpin_generation = "ulpin_generation"
    conflict_detection = "conflict_detection"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    job_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.source_id"))
    parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.parcel_id"))
    job_type = Column(
        SAEnum(JobType, name="job_type", native_enum=True, create_type=False),
        nullable=False,
    )
    status = Column(
        SAEnum(JobStatus, name="job_status", native_enum=True, create_type=False),
        nullable=False,
        default=JobStatus.pending,
    )
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    confidence_score = Column(Numeric(4, 3))
    result_metadata = Column(JSONB, default=dict)
    error_message = Column(Text)
    worker_node = Column(String(50))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
