# backend/app/utils/maharashtra_seed_data.py
# Seeds 20 real Maharashtra locations with parcels, buildings, 3D units and
# ownership records, replacing any existing demo data.
# Run: docker compose exec backend python -m app.utils.maharashtra_seed_data
import uuid
from datetime import date

from geoalchemy2 import WKTElement
from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Building, Owner, OwnershipRecord, Parcel, Unit, User
from app.models.owner import OwnerType
from app.models.building import BuildingType
from app.models.parcel import ParcelStatus, ParcelType
from app.models.unit import UnitType
from app.models.ownership import RightsType
from app.models.user import UserRole
from app.services.geometry_service import box_polyhedral_surface_wkt
from app.services.ulpin_generator import generate_ulpin
from app.utils.geo_utils import deg2_area_to_m2

STATE_CODE = "27"

# Real Maharashtra locations with coordinates
MAHARASHTRA_LOCATIONS = [
    # (village_name, lon, lat, district_code, village_code)
    ("Mumbai Central", 72.8777, 19.0760, "023", "456789"),
    ("Pune Camp", 73.8567, 18.5204, "024", "123456"),
    ("Nashik Road", 73.7898, 19.9975, "025", "654321"),
    ("Nagpur Sadar", 79.0882, 21.1458, "026", "987654"),
    ("Thane Station", 72.9758, 19.2183, "027", "111222"),
    ("Kalyan West", 73.1302, 19.2403, "028", "333444"),
    ("Aurangabad City", 75.3433, 19.8762, "029", "555666"),
    ("Solapur North", 75.9064, 17.6599, "030", "777888"),
    ("Amravati Camp", 77.7523, 20.9320, "031", "999000"),
    ("Kolhapur Mahal", 74.2436, 16.7050, "032", "112233"),
    ("Sangli Miraj", 74.6040, 16.8602, "033", "445566"),
    ("Jalgaon City", 75.5626, 21.0077, "034", "778899"),
    ("Akola City", 77.0085, 20.7096, "035", "223344"),
    ("Latur Station", 76.5604, 18.4088, "036", "556677"),
    ("Dhule City", 74.7749, 20.9042, "037", "889900"),
    ("Ahmednagar City", 74.7496, 19.0948, "038", "334455"),
    ("Chandrapur City", 79.2961, 19.9615, "039", "667788"),
    ("Parbhani City", 76.7767, 19.2608, "040", "990011"),
    ("Jalna City", 75.8800, 19.8410, "041", "224466"),
    ("Bhusawal Town", 75.8013, 21.0455, "042", "557733"),
]


def create_building_footprint(center_lon, center_lat, width_deg=0.001):
    """Create a rectangular footprint around a point."""
    half = width_deg / 2
    return Polygon([
        (center_lon - half, center_lat - half),
        (center_lon + half, center_lat - half),
        (center_lon + half, center_lat + half),
        (center_lon - half, center_lat + half),
        (center_lon - half, center_lat - half),
    ])


def seed_maharashtra_data(db: Session):
    # Create admin
    admin = db.query(User).filter(User.email == "admin@ulpin.gov.in").first()
    if not admin:
        from app.services.auth_service import hash_password

        admin = User(
            user_id=uuid.uuid4(),
            email="admin@ulpin.gov.in",
            password_hash=hash_password("admin123"),
            role=UserRole.admin,
            full_name="System Administrator",
        )
        db.add(admin)
        db.flush()

    # Create 20 owners
    owner_data = [
        ("Ramesh Patel", "individual", {"phone": "+91-9876543210", "address": "Mumbai"}),
        ("Skyline Developers Pvt Ltd", "corporation", {"phone": "+91-22-12345678", "address": "Pune"}),
        ("Mumbai Metro Rail Corp", "government", {"phone": "+91-22-87654321", "address": "Mumbai"}),
        ("Sunita Sharma", "individual", {"phone": "+91-9876543211", "address": "Nashik"}),
        ("Green Valley Housing Society", "corporation", {"phone": "+91-253-1234567", "address": "Nashik"}),
        ("Nagpur Municipal Corp", "government", {"phone": "+91-712-1234567", "address": "Nagpur"}),
        ("Vikram Desai", "individual", {"phone": "+91-9876543212", "address": "Thane"}),
        ("Thane Smart City Ltd", "corporation", {"phone": "+91-22-23456789", "address": "Thane"}),
        ("Aurangabad Development Auth", "government", {"phone": "+91-240-1234567", "address": "Aurangabad"}),
        ("Priya Kulkarni", "individual", {"phone": "+91-9876543213", "address": "Pune"}),
        ("Pune Housing Board", "government", {"phone": "+91-20-12345678", "address": "Pune"}),
        ("Rajesh Gupta", "individual", {"phone": "+91-9876543214", "address": "Kalyan"}),
        ("Kalyan Builders", "corporation", {"phone": "+91-251-1234567", "address": "Kalyan"}),
        ("Deepa Joshi", "individual", {"phone": "+91-9876543215", "address": "Solapur"}),
        ("Solapur Urban Dev Corp", "government", {"phone": "+91-217-1234567", "address": "Solapur"}),
        ("Amit Patil", "individual", {"phone": "+91-9876543216", "address": "Kolhapur"}),
        ("Kolhapur Real Estate", "corporation", {"phone": "+91-231-1234567", "address": "Kolhapur"}),
        ("Jalgaon Municipal Corp", "government", {"phone": "+91-257-1234567", "address": "Jalgaon"}),
        ("Neha Sharma", "individual", {"phone": "+91-9876543217", "address": "Akola"}),
        ("Akola Housing Society", "corporation", {"phone": "+91-724-1234567", "address": "Akola"}),
    ]

    owners = []
    for name, otype, contact in owner_data:
        o = Owner(
            owner_id=uuid.uuid4(),
            owner_type=OwnerType(otype),
            name=name,
            contact=contact,
            is_verified=True,
        )
        owners.append(o)
        db.add(o)
    db.flush()

    parcel_count = 0
    building_count = 0
    unit_count = 0

    for loc_idx, (village_name, lon, lat, district, village) in enumerate(MAHARASHTRA_LOCATIONS):
        # Create 2 parcels per location
        for p_idx in range(2):
            parcel_count += 1
            parcel_seq = loc_idx * 2 + p_idx + 1

            offset_lon = lon + (p_idx * 0.002)
            offset_lat = lat + (p_idx * 0.002)
            footprint = create_building_footprint(offset_lon, offset_lat, 0.001)

            parcel_ulpin = generate_ulpin(STATE_CODE, district, village, parcel_seq, 0, 0)

            p = Parcel(
                parcel_id=uuid.uuid4(),
                ulpin=parcel_ulpin,
                village_code=village,
                geom_2d=WKTElement(f"SRID=4326;{footprint.wkt}", srid=4326),
                area_sqm=round(deg2_area_to_m2(footprint.area, offset_lat), 2),
                parcel_type=ParcelType.multi_storey if p_idx == 0 else ParcelType.surface,
                status=ParcelStatus.verified,
                created_by=admin.user_id,
            )
            db.add(p)
            db.flush()

            # Create 2 buildings per parcel
            for b_idx in range(2):
                building_count += 1
                b_center_lon = offset_lon + (b_idx * 0.0005)
                b_center_lat = offset_lat + (b_idx * 0.0005)
                b_footprint = create_building_footprint(b_center_lon, b_center_lat, 0.0008)

                floors_above = 5 + (loc_idx % 8)  # 5-12 floors
                floors_below = 1 if loc_idx % 3 == 0 else 0  # Some have basements
                height = floors_above * 3.0 + floors_below * 3.0

                b = Building(
                    building_id=uuid.uuid4(),
                    parcel_id=p.parcel_id,
                    building_name=f"{village_name} Tower {b_idx + 1}",
                    footprint=WKTElement(f"SRID=4326;{b_footprint.wkt}", srid=4326),
                    height_m=height,
                    floors_above_ground=floors_above,
                    floors_below_ground=floors_below,
                    building_type=BuildingType.residential if b_idx == 0 else BuildingType.mixed,
                    extracted_by_ml=True,
                    confidence_score=0.92 + (loc_idx % 8) * 0.01,
                )
                db.add(b)
                db.flush()

                # Units for each floor: two side-by-side halves of the footprint
                # (identical volumes on the same floor would be false conflicts).
                minx, miny, maxx, maxy = b_footprint.bounds
                midx = (minx + maxx) / 2
                unit_boxes = [
                    (minx, miny, midx, maxy),   # unit 1: west half
                    (midx, miny, maxx, maxy),   # unit 2: east half
                ]

                for floor in range(1, floors_above + 1):
                    base_h = (floor - 1) * 3.0
                    top_h = floor * 3.0
                    for unit, (ux0, uy0, ux1, uy1) in enumerate(unit_boxes, start=1):
                        unit_count += 1
                        # Unit number continues across buildings of the same
                        # parcel (1-2 = building 1, 3-4 = building 2) so every
                        # unit ULPIN stays unique within the parcel.
                        unit_index = b_idx * 2 + unit
                        unit_ulpin = generate_ulpin(
                            STATE_CODE, district, village, parcel_seq, floor, unit_index
                        )
                        volume_wkt = box_polyhedral_surface_wkt(ux0, uy0, ux1, uy1, base_h, top_h)
                        area_sqm = round(deg2_area_to_m2((ux1 - ux0) * (uy1 - uy0), uy0), 2)

                        u = Unit(
                            unit_id=uuid.uuid4(),
                            building_id=b.building_id,
                            parent_parcel_id=p.parcel_id,
                            unit_ulpin=unit_ulpin,
                            volume_3d=WKTElement(
                                f"SRID=4326;{volume_wkt}", srid=4326, extended=True
                            ),
                            floor_number=floor,
                            floor_label=f"F{floor:02d}",
                            unit_type=UnitType.apartment if unit == 1 else UnitType.shop,
                            area_sqm=area_sqm,
                            volume_cubm=round(area_sqm * 3.0, 2),
                            height_min_m=base_h,
                            height_max_m=top_h,
                            status=ParcelStatus.verified,
                        )
                        db.add(u)
                        db.flush()

                        owner = owners[unit_count % len(owners)]
                        rights = ["full_ownership", "lease", "joint"][unit_count % 3]

                        o = OwnershipRecord(
                            ownership_id=uuid.uuid4(),
                            unit_id=u.unit_id,
                            owner_id=owner.owner_id,
                            rights_type=RightsType(rights),
                            share_percentage=100.0 if rights == "full_ownership" else 50.0,
                            valid_from=date(2020, 1, 1),
                            valid_to=None,
                            registered_by=admin.user_id,
                        )
                        db.add(o)

    db.commit()

    print(f"Seeded Maharashtra data:")
    print(f"   {len(MAHARASHTRA_LOCATIONS)} locations")
    print(f"   {parcel_count} parcels")
    print(f"   {building_count} buildings")
    print(f"   {unit_count} units with ULPINs")
    print(f"   {len(owners)} owners")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        print("Clearing old data...")
        db.query(OwnershipRecord).delete()
        db.query(Unit).delete()
        db.query(Building).delete()
        db.query(Parcel).delete()
        db.query(Owner).delete()
        db.commit()

        seed_maharashtra_data(db)
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
