"""Celery ML pipeline (Section 9 + Section 15 notes).

Mock chained pipeline:
    extract_buildings | segment_floors | delineate_volumes
    | validate_topology | generate_ulpins | detect_conflicts

Each step reports progress via self.update_state(state="PROGRESS", meta=...)
(for the /ws/jobs/{id} WebSocket) and persists results/conflicts to Postgres.
"""
from __future__ import annotations

import datetime as dt
import socket
import uuid as uuid_module

from celery import Celery, chain
from geoalchemy2 import WKTElement

from app.config import get_settings
from app.database import SessionLocal
from app.models import (
    Building,
    ConflictAlert,
    JobStatus,
    ProcessingJob,
    Unit,
)
from app.services.conflict_service import (
    detect_conflicts_for_parcel,
    detect_conflicts_for_unit,
)
from app.services.ulpin_generator import generate_ulpin, parse_ulpin
from app.ml.building_extractor import extract_buildings
from app.ml.floor_segmenter import segment_floors
from app.ml.vertical_delineator import delineate_volumes
from app.ml.topology_validator import validate_topology

settings = get_settings()

celery_app = Celery(
    "ulpin_ml_pipeline",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_track_started=True,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    worker_prefetch_multiplier=1,
    task_default_queue="ml",
)

UNITS_PER_FLOOR = 2


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _progress(self, ctx: dict, step: str, percent: int, message: str) -> None:
    """Publish progress to Celery state AND to the processing_jobs row."""
    meta = {"step": step, "percent": percent, "message": message}
    self.update_state(state="PROGRESS", meta=meta)
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, uuid_module.UUID(ctx["job_id"]))
        if job is not None:
            result_meta = dict(job.result_metadata or {})
            result_meta["progress"] = meta
            result_meta.setdefault("steps", {})[step] = meta
            job.result_metadata = result_meta
            db.commit()
    finally:
        db.close()


def _fail_job(ctx: dict, exc: Exception) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, uuid_module.UUID(ctx["job_id"]))
        if job is not None:
            job.status = JobStatus.failed
            job.error_message = f"{type(exc).__name__}: {exc}"
            job.completed_at = dt.datetime.now(dt.timezone.utc)
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# pipeline tasks
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="app.tasks.ml_pipeline.extract_buildings")
def extract_buildings_task(self, ctx: dict) -> dict:
    try:
        _progress(self, ctx, "extract_buildings", 10, "loading orthomosaic")
        mock_buildings = extract_buildings(
            count=2,
            progress_cb=lambda p, m: _progress(self, ctx, "extract_buildings", p, m),
        )
        building_ids = []
        db = SessionLocal()
        try:
            if ctx.get("parcel_id"):
                parcel_id = uuid_module.UUID(ctx["parcel_id"])
                for mb in mock_buildings:
                    building = Building(
                        building_id=uuid_module.uuid4(),
                        parcel_id=parcel_id,
                        building_name=f"ML Building {mb['footprint'].centroid.x:.4f}",
                        footprint=WKTElement(f"SRID=4326;{mb['footprint_wkt']}", srid=4326),
                        height_m=45.0,
                        floors_above_ground=5,
                        floors_below_ground=1,
                        extracted_by_ml=True,
                        confidence_score=mb["confidence"],
                        metadata_={"mock": True, "area_sqm": mb["area_sqm"]},
                    )
                    db.add(building)
                    db.flush()
                    building_ids.append(str(building.building_id))
            job = db.get(ProcessingJob, uuid_module.UUID(ctx["job_id"]))
            if job is not None:
                job.status = JobStatus.running
                job.started_at = dt.datetime.now(dt.timezone.utc)
                job.worker_node = socket.gethostname()
                db.commit()
        finally:
            db.close()
        ctx["building_ids"] = building_ids
        ctx["mock_buildings"] = [
            {"footprint_wkt": mb["footprint_wkt"], "confidence": mb["confidence"]}
            for mb in mock_buildings
        ]
        _progress(self, ctx, "extract_buildings", 35, "building extraction complete")
        return ctx
    except Exception as exc:  # noqa: BLE001
        _fail_job(ctx, exc)
        raise


@celery_app.task(bind=True, name="app.tasks.ml_pipeline.segment_floors")
def segment_floors_task(self, ctx: dict) -> dict:
    try:
        floors = segment_floors(
            floors_above_ground=5,
            floors_below_ground=1,
            progress_cb=lambda p, m: _progress(self, ctx, "segment_floors", p, m),
        )
        ctx["floors"] = floors
        _progress(self, ctx, "segment_floors", 52, "floor segmentation complete")
        return ctx
    except Exception as exc:  # noqa: BLE001
        _fail_job(ctx, exc)
        raise


@celery_app.task(bind=True, name="app.tasks.ml_pipeline.delineate_volumes")
def delineate_volumes_task(self, ctx: dict) -> dict:
    try:
        db = SessionLocal()
        try:
            building_ids = ctx.get("building_ids") or []
            if not building_ids and ctx.get("parcel_id"):
                buildings = (
                    db.query(Building)
                    .filter(Building.parcel_id == uuid_module.UUID(ctx["parcel_id"]))
                    .all()
                )
                building_ids = [str(b.building_id) for b in buildings[-2:]]
            created_units = []
            for bid in building_ids:
                building = db.get(Building, uuid_module.UUID(bid))
                if building is None or building.footprint is None:
                    continue
                from geoalchemy2.shape import to_shape

                footprint_wkt = to_shape(building.footprint).wkt
                volumes = delineate_volumes(
                    footprint_wkt,
                    ctx["floors"],
                    units_per_floor=UNITS_PER_FLOOR,
                    progress_cb=lambda p, m: _progress(self, ctx, "delineate_volumes", p, m),
                )
                parcel_seq = _parcel_seq(db, building.parcel_id)
                for vol in volumes:
                    # Idempotency: skip if a mock unit already exists for this
                    # building + floor + index.
                    exists = (
                        db.query(Unit)
                        .filter(
                            Unit.building_id == building.building_id,
                            Unit.floor_number == vol["floor_number"],
                            Unit.metadata_["unit_index"].astext == str(vol["unit_index"]),
                        )
                        .first()
                    )
                    if exists:
                        continue
                    ulpin = generate_ulpin(
                        "27", "023", "456789", parcel_seq, vol["floor_number"], vol["unit_index"]
                    )
                    unit = Unit(
                        unit_id=uuid_module.uuid4(),
                        building_id=building.building_id,
                        parent_parcel_id=building.parcel_id,
                        unit_ulpin=ulpin,
                        volume_3d=WKTElement(
                            f"SRID=4326;{vol['volume_wkt']}", srid=4326, extended=True
                        ),
                        floor_number=vol["floor_number"],
                        floor_label=vol["floor_label"],
                        unit_type=vol["unit_type"],
                        area_sqm=vol["area_sqm"],
                        volume_cubm=vol["volume_cubm"],
                        height_min_m=vol["z_min"],
                        height_max_m=vol["z_max"],
                        metadata_={"unit_index": vol["unit_index"], "mock": True},
                    )
                    db.add(unit)
                    db.flush()
                    created_units.append(str(unit.unit_id))
            db.commit()
        finally:
            db.close()
        ctx["created_units"] = created_units
        _progress(self, ctx, "delineate_volumes", 75, "vertical delineation complete")
        return ctx
    except Exception as exc:  # noqa: BLE001
        _fail_job(ctx, exc)
        raise


@celery_app.task(bind=True, name="app.tasks.ml_pipeline.validate_topology")
def validate_topology_task(self, ctx: dict) -> dict:
    try:
        db = SessionLocal()
        try:
            units = [
                db.get(Unit, uuid_module.UUID(uid))
                for uid in ctx.get("created_units", [])
            ]
            volumes = [
                {
                    "unit_index": (u.metadata_ or {}).get("unit_index", i + 1),
                    "floor_number": u.floor_number,
                    "volume_cubm": float(u.volume_cubm) if u.volume_cubm else 0.0,
                    "bbox": _unit_bbox(u),
                }
                for i, u in enumerate(units)
                if u is not None
            ]
        finally:
            db.close()
        report = validate_topology(
            volumes,
            progress_cb=lambda p, m: _progress(self, ctx, "validate_topology", p, m),
        )
        ctx["topology"] = report
        _progress(self, ctx, "validate_topology", 88, "topology validation complete")
        return ctx
    except Exception as exc:  # noqa: BLE001
        _fail_job(ctx, exc)
        raise


@celery_app.task(bind=True, name="app.tasks.ml_pipeline.generate_ulpins")
def generate_ulpins_task(self, ctx: dict) -> dict:
    try:
        db = SessionLocal()
        try:
            ulpins = {}
            for uid in ctx.get("created_units", []):
                unit = db.get(Unit, uuid_module.UUID(uid))
                if unit is None:
                    continue
                if not unit.unit_ulpin:
                    parcel_seq = _parcel_seq(db, unit.parent_parcel_id)
                    unit.unit_ulpin = generate_ulpin(
                        "27",
                        "023",
                        "456789",
                        parcel_seq,
                        unit.floor_number or 0,
                        int((unit.metadata_ or {}).get("unit_index", 1)),
                    )
                ulpins[str(unit.unit_id)] = unit.unit_ulpin
            db.commit()
        finally:
            db.close()
        ctx["ulpins"] = ulpins
        _progress(self, ctx, "generate_ulpins", 93, f"assigned {len(ulpins)} ULPINs")
        return ctx
    except Exception as exc:  # noqa: BLE001
        _fail_job(ctx, exc)
        raise


@celery_app.task(bind=True, name="app.tasks.ml_pipeline.detect_conflicts")
def detect_conflicts_task(self, ctx: dict) -> dict:
    try:
        job_uuid = uuid_module.UUID(ctx["job_id"])
        db = SessionLocal()
        alerts: list[ConflictAlert] = []
        try:
            if ctx.get("parcel_id"):
                alerts = detect_conflicts_for_parcel(
                    db, uuid_module.UUID(ctx["parcel_id"]), job_id=job_uuid
                )
            else:
                for uid in ctx.get("created_units", []):
                    alerts.extend(
                        detect_conflicts_for_unit(db, uuid_module.UUID(uid), job_id=job_uuid)
                    )

            job = db.get(ProcessingJob, job_uuid)
            if job is not None:
                topology = ctx.get("topology") or {}
                job.status = JobStatus.completed
                job.completed_at = dt.datetime.now(dt.timezone.utc)
                job.confidence_score = 0.94 if topology.get("valid", True) else 0.61
                job.result_metadata = {
                    "progress": {"step": "detect_conflicts", "percent": 100,
                                 "message": "pipeline complete"},
                    "steps": (job.result_metadata or {}).get("steps", {}),
                    "topology": topology,
                    "ulpins": ctx.get("ulpins", {}),
                    "conflicts_detected": len(alerts),
                    "mock": True,
                }
                db.commit()
        finally:
            db.close()
        ctx["conflicts"] = [str(a.alert_id) for a in alerts]
        _progress(self, ctx, "detect_conflicts", 100, "conflict detection complete")
        return ctx
    except Exception as exc:  # noqa: BLE001
        _fail_job(ctx, exc)
        raise


# ---------------------------------------------------------------------------
# pipeline entry point
# ---------------------------------------------------------------------------

def _parcel_seq(db, parcel_id) -> int:
    from app.models import Parcel

    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        return 1
    parsed = parse_ulpin(parcel.ulpin)
    if parsed:
        return int(parsed["parcel"])
    return 1


def _unit_bbox(unit: Unit) -> tuple:
    """Approximate a unit bbox from its height range and parent parcel origin.

    Avoids parsing PolyhedralSurfaceZ WKT with GEOS (unsupported); good enough
    for the mock topology validator.
    """
    zmin = float(unit.height_min_m) if unit.height_min_m is not None else 0.0
    zmax = float(unit.height_max_m) if unit.height_max_m is not None else 3.0
    base = 72.8777
    lat = 19.0760
    idx = int((unit.metadata_ or {}).get("unit_index", 1)) - 1
    minx = base + idx * 0.0004
    return (minx, lat, minx + 0.0004, lat + 0.0009, zmin, zmax)


def run_pipeline_chain(job_id: str, source_id: str | None, parcel_id: str | None):
    """Enqueue the full mock pipeline for a processing job."""
    ctx = {"job_id": job_id, "source_id": source_id, "parcel_id": parcel_id}
    workflow = chain(
        extract_buildings_task.s(ctx),
        segment_floors_task.s(),
        delineate_volumes_task.s(),
        validate_topology_task.s(),
        generate_ulpins_task.s(),
        detect_conflicts_task.s(),
    )
    return workflow.apply_async()
