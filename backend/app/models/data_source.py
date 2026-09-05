import enum
import uuid

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class SourceType(str, enum.Enum):
    drone_image = "drone_image"
    lidar = "lidar"
    gis_shapefile = "gis_shapefile"
    floor_plan = "floor_plan"
    gnss_log = "gnss_log"
    dem = "dem"
    survey_sketch = "survey_sketch"


class ProcessingStatus(str, enum.Enum):
    uploaded = "uploaded"
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class DataSource(Base):
    __tablename__ = "data_sources"

    source_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    source_type = Column(
        SAEnum(SourceType, name="source_type", native_enum=True, create_type=False),
        nullable=False,
    )
    file_url = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger)
    metadata_ = Column("metadata", JSONB, default=dict)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    parcel_id = Column(UUID(as_uuid=True), ForeignKey("parcels.parcel_id"))
    processing_status = Column(
        SAEnum(ProcessingStatus, name="processing_status", native_enum=True, create_type=False),
        nullable=False,
        default=ProcessingStatus.uploaded,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
