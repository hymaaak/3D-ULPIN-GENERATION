# SIH26011 — 3D ULPIN Generation & Vertical Property Mapping System

A web-based 3D cadastral prototype for the Smart India Hackathon (SIH26011).
It ingests drone imagery, LiDAR point clouds, GIS shapefiles, and building
floor plans; runs (mocked) AI/ML pipelines to extract buildings, segment
floors, and delineate 3D volumes; generates hierarchical 3D-ULPINs; and
visualizes everything in an interactive 3D web viewer with ownership mapping
and conflict detection. Fully containerized with Docker Compose and
pre-loaded with mock data.

## Prerequisites

- Docker (v27+)
- Docker Compose (v2.29+)

## Quickstart

```bash
cp .env.example .env
docker compose up --build
```

Then open:

| Service      | URL                        |
|--------------|----------------------------|
| Frontend     | http://localhost (via nginx) or http://localhost:5173 (Vite dev server) |
| API docs     | http://localhost:8000/docs (Swagger UI) |
| MinIO console| http://localhost:9001 (login from `.env`: `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`) |

Default admin login (from the seed): `admin@ulpin.gov.in` / `admin123`.

## Seeding mock data

The demo dataset (10 parcels, 3 buildings, 15 units with unit-level ULPINs,
5 owners, 10 ownership records) can be loaded either through the backend
seed module (recommended — Section 14):

```bash
docker compose exec backend python -m app.utils.seed_data
```

or by applying the SQL seed directly (matches
`data/mock/sample_parcels.geojson`):

```bash
docker compose exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB < data/seed/seed_data.sql
```

MinIO buckets `ulpin-raw-uploads` and `ulpin-processed` are created
automatically on first startup by the one-shot `minio-init` service (Section
17 pitfall fix: `mc alias set local http://minio:9000 && mc mb ...`).

## Mock-data disclaimer

Per Section 13 Phase 5, **all ML pipelines are mocked with pre-computed
results** — building extraction, floor segmentation, vertical delineation,
and topology validation return cached/demo outputs with simulated progress.
Nothing is actually inferred from uploaded files. The binary files under
`data/mock/` (`sample_drone.tif`, `sample_lidar.laz`, `sample_floorplan.dwg`)
are small placeholders (a few hundred bytes) so the upload UI has files to
demo; only `sample_parcels.geojson` is real data, consumed by the seed.

## Testing checklist (Section 16)

API tests (via Swagger UI at `/docs`):
- Register → Login → access protected endpoint
- Create parcel with 2D polygon
- Create building linked to parcel
- Create unit with ULPIN
- Upload file → trigger job → check status
- Search ULPIN → get unit detail
- Query 3D conflicts

Frontend tests:
- Login page → redirect to dashboard
- Upload file → see progress → job complete
- 3D viewer loads → rotate/zoom → click building
- ULPIN popup shows correct data
- Layer toggles work (surface/building/underground)
- Search finds parcel by ULPIN
- Admin panel shows user list

## Demo script (12 minutes, Section 16)

1. **Problem (1 min)** — show the 2D map limitation, explain the vertical ownership crisis
2. **Upload (2 min)** — drag drone image + LiDAR, show upload progress
3. **Processing (1 min)** — job monitor with step indicators
4. **3D Viewer (3 min)** — hero moment: fly through building, click floor, show ULPIN
5. **Ownership (1 min)** — toggle owner, show certificate
6. **Conflict (1 min)** — show red alert, explain detection
7. **Search (1 min)** — type a ULPIN, instant result
8. **Impact (2 min)** — scalability slide, Ministry integration roadmap

## Layout

- `docker-compose.yml`, `nginx.conf`, `.env.example` — root infrastructure
- `backend/` — FastAPI + Celery + Alembic/PostGIS init (owned by backend agent)
- `frontend/` — React + Vite SPA (owned by frontend agent)
- `data/mock/` — demo upload placeholders + `sample_parcels.geojson`
- `data/seed/seed_data.sql` — SQL demo seed
