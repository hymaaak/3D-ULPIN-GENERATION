"""FastAPI entry point: app factory, CORS, routers, /health, job WebSocket."""
import asyncio
import logging
import uuid as uuid_module

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import SessionLocal
from app.models import JobStatus, ProcessingJob
from app.routers import (
    auth,
    buildings,
    conflicts,
    jobs,
    ownership,
    owners,
    parcels,
    search,
    tiles,
    units,
    upload,
)

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="SIH26011 — 3D ULPIN Generation & Vertical Property Mapping",
    version="1.0.0",
    description="Backend for the 3D cadastral prototype (hackathon demo).",
)

# CORS: allow_origins=["*"] for dev (Section 17)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    """Create MinIO buckets if missing (Section 17 pitfall)."""
    try:
        from app.services.file_service import ensure_buckets

        created = ensure_buckets()
        if created:
            logger.info("Created MinIO buckets: %s", created)
    except Exception as exc:  # noqa: BLE001
        logger.warning("MinIO not reachable at startup (buckets not created): %s", exc)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app_env": settings.APP_ENV,
        "database": settings.POSTGRES_HOST,
        "redis": settings.REDIS_HOST,
        "minio": settings.MINIO_ENDPOINT,
    }


for module in (
    auth,
    parcels,
    buildings,
    units,
    ownership,
    owners,
    upload,
    jobs,
    conflicts,
    search,
    tiles,
):
    app.include_router(module.router)


_TERMINAL_STATES = (JobStatus.completed, JobStatus.failed, JobStatus.cancelled)


@app.websocket("/ws/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str) -> None:
    """Live job progress for JobMonitor.jsx (Section 8: WS /ws/jobs/{id})."""
    await websocket.accept()
    try:
        job_uuid = uuid_module.UUID(job_id)
    except ValueError:
        await websocket.send_json({"error": "invalid job id"})
        await websocket.close()
        return

    try:
        while True:
            db = SessionLocal()
            try:
                job = db.get(ProcessingJob, job_uuid)
                if job is None:
                    await websocket.send_json({"error": "job not found"})
                    break
                meta = job.result_metadata if isinstance(job.result_metadata, dict) else {}
                await websocket.send_json(
                    {
                        "job_id": str(job.job_id),
                        "job_type": job.job_type.value,
                        "status": job.status.value,
                        "step": (meta.get("progress") or {}).get("step"),
                        "percent": (meta.get("progress") or {}).get("percent", 0),
                        "message": (meta.get("progress") or {}).get("message"),
                        "confidence_score": (
                            float(job.confidence_score) if job.confidence_score else None
                        ),
                        "error_message": job.error_message,
                    }
                )
                if job.status in _TERMINAL_STATES:
                    break
            finally:
                db.close()
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass
