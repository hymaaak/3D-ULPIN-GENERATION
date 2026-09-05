import uuid as uuid_module
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.processing_job import JobStatus, JobType


class JobTriggerRequest(BaseModel):
    source_id: uuid_module.UUID | None = None
    parcel_id: uuid_module.UUID | None = None
    job_type: JobType = JobType.building_extraction


class ProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid_module.UUID
    source_id: uuid_module.UUID | None = None
    parcel_id: uuid_module.UUID | None = None
    job_type: JobType
    status: JobStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    confidence_score: float | None = None
    result_metadata: dict | None = None
    error_message: str | None = None
    worker_node: str | None = None
    created_at: datetime
