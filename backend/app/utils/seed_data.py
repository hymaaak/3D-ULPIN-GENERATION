"""Mock demo data seed (Section 14). Run with: python -m app.utils.seed_data

Creates: 1 admin user, 5 owners, 5 parcels, 3 buildings, per-floor units with
6-face PolyhedralSurfaceZ volumes, and ownership records for the first 10 units.
"""
from __future__ import annotations

import argparse
import uuid
from datetime import date

from geoalchemy2 import WKTElement
from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import (
    Building,
    BuildingType,
    Owner,
    OwnerType,
    OwnershipRecord,
    Parcel,
    ParcelStatus,
    ParcelType,
    RightsType,
    Unit,
    UnitType,
    User,
    UserRole,
)
from app.services.geometry_service import box_polyhedral_surface_wkt
from app.services.ulpin_generator import generate_ulpin
from app.utils.geo_utils import deg2_area_to_m2

ADMIN_EMAIL = "admin@ulpin.gov.in"
ADMIN_PASSWORD = "admin123"  # demo only; overridden in production
STATE_CODE = "27"  # Maharashtra
DISTRICT_CODE = "023"
VILLAGE_CODE = "456789"


def _hash_password(password: str) -> str:
    try:
        from app.services.auth_service import hash_password

        return hash_password(password)
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: passlib unavailable ({exc}); using placeholder hash")
        return "$2b$12$" + "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6A7B"


def _unit_volume_wkt(
    lon: float,
    lat: float,
    unit_index: int,
    floor: int,
    floor_height: float = 3.0,
) -> str:
    """Extrude a half-parcel unit box (EPSG:4326 local offsets, tiny coords)."""
    size = 0.001  # parcel size in degrees (~110 m)
    mid = lon + size / 2.0
    minx = lon if unit_index == 1 else mid
    maxx = mid if unit_index == 1 else lon + size
    zmin = (floor - 1) * floor_height
    zmax = floor * floor_height
    return box_polyhedral_surface_wkt(minx, lat, maxx, lat + size, zmin, zmax)


def seed_demo_data(db: Session) -> None:
    existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    if existing is not None:
        print("Demo data already seeded (admin user exists). Skipping.")
        return

    # Create admin user (Section 14; real bcrypt hash instead of "$2b$12$...")
    admin = User(
        user_id=uuid.uuid4(),
        email=ADMIN_EMAIL,
        password_hash=_hash_password(ADMIN_PASSWORD),
        role=UserRole.admin,
        full_name="System Administrator",
    )
    db.add(admin)

    # Create owners
    owners = [
        Owner(
            owner_id=uuid.uuid4(),
            owner_type=OwnerType.individual,
            name="Ramesh Patel",
            contact={"phone": "+91-9876543210", "address": "Mumbai"},
        ),
        Owner(
            owner_id=uuid.uuid4(),
            owner_type=OwnerType.corporation,
            name="Skyline Developers Pvt Ltd",
            contact={"phone": "+91-22-12345678"},
        ),
        Owner(
            owner_id=uuid.uuid4(),
            owner_type=OwnerType.government,
            name="Mumbai Metro Rail Corp",
            contact={"phone": "+91-22-87654321"},
        ),
        Owner(
            owner_id=uuid.uuid4(),
            owner_type=OwnerType.individual,
            name="Sunita Deshmukh",
            contact={"phone": "+91-9822011223", "address": "Andheri, Mumbai"},
        ),
        Owner(
            owner_id=uuid.uuid4(),
            owner_type=OwnerType.trust,
            name="Shree Ganesh Charitable Trust",
            contact={"phone": "+91-22-44556677"},
        ),
    ]
    for o in owners:
        db.add(o)
    db.flush()

    # Create parcels
    parcels = []
    for i in range(5):
        lon = 72.8777 + (i * 0.001)
        lat = 19.0760 + (i * 0.001)
        footprint = Polygon(
            [
                (lon, lat),
                (lon + 0.001, lat),
                (lon + 0.001, lat + 0.001),
                (lon, lat + 0.001),
                (lon, lat),
            ]
        )
        p = Parcel(
            parcel_id=uuid.uuid4(),
            ulpin=generate_ulpin(STATE_CODE, DISTRICT_CODE, VILLAGE_CODE, i + 1, 0, 0),
            legacy_survey_no=f"SN/{100 + i}",
            village_code=VILLAGE_CODE,
            geom_2d=WKTElement(f"SRID=4326;{footprint.wkt}", srid=4326),
            area_sqm=round(deg2_area_to_m2(footprint.area, lat), 2),
            parcel_type=ParcelType.multi_storey if i < 3 else ParcelType.surface,
            status=ParcelStatus.verified,
            metadata_={"seed": True},
            created_by=admin.user_id,
        )
        parcels.append(p)
        db.add(p)
    db.commit()

    # Create buildings
    buildings = []
    for i, parcel in enumerate(parcels[:3]):
        b = Building(
            building_id=uuid.uuid4(),
            parcel_id=parcel.parcel_id,
            building_name=f"Building {i + 1}",
            footprint=parcel.geom_2d,
            height_m=45.0 + (i * 10),
            floors_above_ground=10 + i,
            floors_below_ground=2,
            construction_year=2010 + i,
            building_type=BuildingType.residential if i == 0 else BuildingType.mixed,
            extracted_by_ml=True,
            confidence_score=0.94,
            metadata_={"seed": True},
        )
        buildings.append(b)
        db.add(b)
    db.commit()

    # Create units with real PolyhedralSurfaceZ volumes
    units = []
    for b in buildings:
        parcel = next(p for p in parcels if p.parcel_id == b.parcel_id)
        # ulpin format: 3D-ULPIN-{state}-{district}-{village}-{parcel}-Fxx-Uyy-cc
        parcel_seq = int(parcel.ulpin.split("-")[5])
        parcel_geom = parcel.geom_2d
        from geoalchemy2.shape import to_shape

        footprint_poly = to_shape(parcel_geom)
        minx, miny, _, _ = footprint_poly.bounds
        size = 0.001
        for floor in range(1, b.floors_above_ground + 1):
            for unit_num in range(1, 3):
                base_h = (floor - 1) * 3.0
                top_h = floor * 3.0
                unit_ulpin = generate_ulpin(
                    STATE_CODE, DISTRICT_CODE, VILLAGE_CODE, parcel_seq, floor, unit_num
                )
                volume_wkt = _unit_volume_wkt(minx, miny, unit_num, floor)
                area_sqm = round(deg2_area_to_m2(size * size / 2.0, miny), 2)
                u = Unit(
                    unit_id=uuid.uuid4(),
                    building_id=b.building_id,
                    parent_parcel_id=parcel.parcel_id,
                    unit_ulpin=unit_ulpin,
                    volume_3d=WKTElement(f"SRID=4326;{volume_wkt}", srid=4326, extended=True),
                    floor_number=floor,
                    floor_label=f"F{floor:02d}",
                    unit_type=UnitType.apartment,
                    area_sqm=area_sqm,
                    volume_cubm=round(area_sqm * 3.0, 2),
                    height_min_m=base_h,
                    height_max_m=top_h,
                    status=ParcelStatus.verified,
                    metadata_={"seed": True, "unit_index": unit_num},
                )
                units.append(u)
                db.add(u)
    db.commit()

    # Create ownership records (first 10 units, round-robin across owners)
    for i, u in enumerate(units[:10]):
        owner = owners[i % len(owners)]
        o = OwnershipRecord(
            ownership_id=uuid.uuid4(),
            unit_id=u.unit_id,
            owner_id=owner.owner_id,
            rights_type=RightsType.full_ownership,
            share_percentage=100.0,
            valid_from=date(2020, 1, 1),
            valid_to=None,
            registered_by=admin.user_id,
        )
        db.add(o)
    db.commit()

    print(
        f"Demo data seeded successfully: 1 user, {len(owners)} owners, "
        f"{len(parcels)} parcels, {len(buildings)} buildings, "
        f"{len(units)} units, 10 ownership records."
    )
    print(f"Admin login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data for the 3D ULPIN prototype")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="drop and recreate all tables before seeding (uses SQLAlchemy metadata)",
    )
    args = parser.parse_args()

    if args.reset:
        print("Dropping and recreating all tables...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
