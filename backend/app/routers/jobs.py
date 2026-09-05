"""Processing jobs: trigger, status, list (Section 8). WebSocket lives in main.py."""
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_role
from app.models import JobStatus, JobType, ProcessingJob, User
from app.schemas.processing_job import JobTriggerRequest, ProcessingJobResponse
from app.utils.geo_utils import model_to_dict

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _to_response(job: ProcessingJob) -> ProcessingJobResponse:
    return ProcessingJobResponse(**model_to_dict(job))


@router.post("/trigger", response_model=ProcessingJobResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_job(
    data: JobTriggerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor")),
):
    job = ProcessingJob(
        source_id=data.source_id,
        parcel_id=data.parcel_id,
        job_type=data.job_type,
        status=JobStatus.pending,
        result_metadata={"progress": {"step": "queued", "percent": 0, "message": "queued"}},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        from app.tasks.ml_pipeline import run_pipeline_chain

        run_pipeline_chain(
            str(job.job_id),
            str(data.source_id) if data.source_id else None,
            str(data.parcel_id) if data.parcel_id else None,
        )
    except Exception as exc:  # noqa: BLE001
        job.status = JobStatus.failed
        job.error_message = f"Failed to enqueue pipeline: {exc}"
        db.commit()
    return _to_response(job)


@router.get("", response_model=list[ProcessingJobResponse])
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    status: JobStatus | None = None,
    job_type: JobType | None = None,
    parcel_id: uuid_module.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ProcessingJob)
    if status:
        query = query.filter(ProcessingJob.status == status)
    if job_type:
        query = query.filter(ProcessingJob.job_type == job_type)
    if parcel_id:
        query = query.filter(ProcessingJob.parcel_id == parcel_id)
    return [
        _to_response(j)
        for j in query.order_by(ProcessingJob.created_at.desc()).offset(skip).limit(limit).all()
    ]


@router.get("/{job_id}", response_model=ProcessingJobResponse)
def get_job(
    job_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_response(job)


@router.post("/{job_id}/cancel", response_model=ProcessingJobResponse)
def cancel_job(
    job_id: uuid_module.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "surveyor")),
):
    job = db.get(ProcessingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in (JobStatus.completed, JobStatus.failed, JobStatus.cancelled):
        raise HTTPException(status_code=400, detail=f"Job already {job.status.value}")
    job.status = JobStatus.cancelled
    db.commit()
    db.refresh(job)
    return _to_response(job)
