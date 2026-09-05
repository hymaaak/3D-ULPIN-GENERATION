"""
government_buildings_seed.py
Seed script using ONLY public government infrastructure data.
All owners are public entities - no private individuals or corporations.

Adapted to this codebase: WKTElement geometry, box_polyhedral_surface_wkt
volumes, model enums, metadata_ column, hash_password, batched commits.

Run: docker compose exec backend python -m app.utils.government_buildings_seed
"""
import math
import uuid
from datetime import date

from geoalchemy2 import WKTElement
from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Building, Owner, OwnershipRecord, Parcel, Unit, User
from app.models.building import BuildingType
from app.models.owner import OwnerType
from app.models.ownership import RightsType
from app.models.parcel import ParcelStatus, ParcelType
from app.models.unit import UnitType
from app.models.user import UserRole
from app.services.geometry_service import box_polyhedral_surface_wkt
from app.services.ulpin_generator import generate_ulpin

STATE_CODE = "27"

# ============================================================
# PUBLIC GOVERNMENT OWNERS ONLY
# ============================================================
PUBLIC_OWNERS = [
    ("Indian Railways", "government", {"department": "Ministry of Railways", "type": "Central PSU", "headquarters": "New Delhi"}),
    ("Pune Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Pune"}),
    ("Mumbai Metropolitan Region Development Authority", "government", {"department": "Urban Development", "type": "Development Authority", "abbreviation": "MMRDA"}),
    ("Maharashtra Industrial Development Corporation", "government", {"department": "Industries", "type": "State PSU", "abbreviation": "MIDC"}),
    ("State Highway Authority Maharashtra", "government", {"department": "Public Works", "type": "State Authority", "abbreviation": "MSRDC"}),
    ("Nagpur Improvement Trust", "government", {"department": "Urban Planning", "type": "Improvement Trust", "city": "Nagpur"}),
    ("Thane Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Thane"}),
    ("Kalyan-Dombivli Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Kalyan-Dombivli"}),
    ("Aurangabad Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Aurangabad"}),
    ("Solapur Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Solapur"}),
    ("Kolhapur Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Kolhapur"}),
    ("Nashik Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Nashik"}),
    ("Jalgaon Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Jalgaon"}),
    ("Akola Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Akola"}),
    ("Latur Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Latur"}),
    ("Dhule Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Dhule"}),
    ("Ahmednagar Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Ahmednagar"}),
    ("Chandrapur Municipal Council", "government", {"department": "Urban Development", "type": "Municipal Council", "jurisdiction": "Chandrapur"}),
    ("Parbhani Municipal Council", "government", {"department": "Urban Development", "type": "Municipal Council", "jurisdiction": "Parbhani"}),
    ("Amravati Municipal Corporation", "government", {"department": "Urban Development", "type": "Municipal Body", "jurisdiction": "Amravati"}),
    ("Ratnagiri Nagarpalika", "government", {"department": "Urban Development", "type": "Nagarpalika", "jurisdiction": "Ratnagiri"}),
    ("Maharashtra Housing and Area Development Authority", "government", {"department": "Housing", "type": "State Authority", "abbreviation": "MHADA"}),
    ("Maharashtra State Electricity Distribution Co Ltd", "government", {"department": "Energy", "type": "State PSU", "abbreviation": "MSEDCL"}),
    ("Maharashtra Water Supply and Sewerage Board", "government", {"department": "Water Supply", "type": "State Board"}),
    ("Maharashtra State Road Transport Corporation", "government", {"department": "Transport", "type": "State PSU", "abbreviation": "MSRTC"}),
]

# ============================================================
# 25 PROFESSIONAL BUILDING TYPES WITH DISTINCT ARCHITECTURE
# ============================================================
# (type_name, category, floors, floor_height_m, color_hex, outline_hex, width_m, depth_m, description)
BUILDING_TYPES = [
    # RESIDENTIAL (5 types)
    ("Affordable Housing Complex", "residential", 8, 3.0, "#2E86AB", "#A8DADC", 45, 30, "MHADA-style LIG/EWS housing with parking podium"),
    ("High-Rise Residential Tower", "residential", 20, 3.2, "#1D3557", "#457B9D", 35, 35, "Luxury apartments with terrace gardens"),
    ("Government Quarters", "residential", 5, 3.0, "#457B9D", "#A8DADC", 40, 25, "Type-IV government staff quarters"),
    ("Senior Citizen Housing", "residential", 4, 3.2, "#6A994E", "#B7CE63", 30, 25, "Old age home with medical facilities"),
    ("Police Housing Colony", "residential", 6, 2.9, "#1B4965", "#5FA8D3", 50, 30, "Police family welfare housing"),

    # COMMERCIAL (5 types)
    ("District Shopping Complex", "commercial", 4, 4.5, "#9B5DE5", "#F15BB5", 60, 50, "Saraf bazaar style shopping complex"),
    ("IT Park Tower", "commercial", 12, 3.8, "#00BBF9", "#00F5D4", 50, 40, "Software technology park with food court"),
    ("Hotel and Convention Centre", "commercial", 10, 3.5, "#FEE440", "#F15BB5", 45, 40, "3-star hotel with banquet for 500"),
    ("Multiplex and Food Court", "commercial", 3, 6.0, "#F15BB5", "#FEE440", 70, 50, "6-screen multiplex with food court"),
    ("Bank and Commercial Offices", "commercial", 8, 3.6, "#00F5D4", "#00BBF9", 40, 35, "SBI main branch with commercial offices"),

    # GOVERNMENT (5 types)
    ("District Collector Office", "government", 5, 4.0, "#E63946", "#F1FAEE", 55, 40, "Collectorate with record room and court"),
    ("Civil Hospital", "government", 6, 4.2, "#D62828", "#F1FAEE", 65, 45, "100-bed civil hospital with trauma centre"),
    ("Government Polytechnic", "government", 4, 4.0, "#F77F00", "#FCBF49", 50, 40, "MSBTE polytechnic with workshops"),
    ("Fire Station and Training Centre", "government", 3, 5.0, "#D00000", "#FFBA08", 35, 30, "Fire station with drill tower"),
    ("Police Station and Lock-up", "government", 3, 3.8, "#003049", "#D62828", 40, 35, "Police station with lock-up and barracks"),

    # INDUSTRIAL (5 types)
    ("MIDC Industrial Shed A", "industrial", 1, 9.0, "#6C757D", "#ADB5BD", 80, 60, "Steel fabrication workshop 24m span"),
    ("MIDC Industrial Shed B", "industrial", 2, 7.5, "#495057", "#CED4DA", 100, 50, "Warehouse with mezzanine office"),
    ("Cold Storage Warehouse", "industrial", 1, 12.0, "#48CAE4", "#90E0EF", 60, 60, "Refrigerated warehouse for agriculture"),
    ("Food Processing Unit", "industrial", 2, 5.5, "#38B000", "#70E000", 55, 45, "FSSAI approved food park"),
    ("Textile Processing Mill", "industrial", 3, 4.8, "#FF6D00", "#FF9E00", 70, 40, "Cotton processing with dyeing unit"),

    # INFRASTRUCTURE (5 types)
    ("Metro Station and Concourse", "infrastructure", 2, 6.0, "#0077B6", "#00B4D8", 40, 120, "Underground metro with 2 platforms"),
    ("Bus Depot and Workshop", "infrastructure", 2, 5.0, "#03045E", "#0077B6", 80, 60, "MSRTC depot with 50 bus capacity"),
    ("Multi-Level Car Parking", "infrastructure", 5, 3.0, "#8D99AE", "#EDF2F4", 45, 40, "Automated car parking structure"),
    ("Water Treatment Plant", "infrastructure", 1, 8.0, "#00B4D8", "#90E0EF", 70, 50, "30 MLD water treatment plant"),
    ("Electric Sub-Station", "infrastructure", 1, 10.0, "#FFC300", "#FFD60A", 50, 40, "132kV MSEDCL sub-station"),
]

# Maharashtra locations (25 — one per building type)
LOCATIONS = [
    ("Nagpur", 79.0882, 21.1458, "026", "987654"),
    ("Pune", 73.8567, 18.5204, "024", "123457"),
    ("Nashik", 73.7898, 19.9975, "025", "654322"),
    ("Aurangabad", 75.3433, 19.8762, "029", "555667"),
    ("Thane", 72.9758, 19.2183, "027", "111223"),
    ("Kalyan", 73.1302, 19.2403, "028", "333445"),
    ("Solapur", 75.9064, 17.6599, "030", "777889"),
    ("Kolhapur", 74.2436, 16.7050, "032", "112234"),
    ("Sangli", 74.6040, 16.8602, "033", "445567"),
    ("Jalgaon", 75.5626, 21.0077, "034", "778900"),
    ("Akola", 77.0085, 20.7096, "035", "223345"),
    ("Latur", 76.5604, 18.4088, "036", "556678"),
    ("Dhule", 74.7749, 20.9042, "037", "889901"),
    ("Ahmednagar", 74.7496, 19.0948, "038", "334456"),
    ("Chandrapur", 79.2961, 19.9615, "039", "667789"),
    ("Parbhani", 76.7767, 19.2608, "040", "990012"),
    ("Jalna", 75.8800, 19.8410, "041", "224467"),
    ("Bhusawal", 75.8013, 21.0455, "042", "557734"),
    ("Amravati", 77.7523, 20.9320, "031", "999001"),
    ("Ratnagiri", 73.3000, 17.0000, "043", "113355"),
    ("Navi Mumbai", 73.0297, 19.0330, "044", "225588"),
    ("Malegaon", 74.5100, 20.5500, "045", "336699"),
    ("Nanded", 77.3200, 19.1500, "046", "447711"),
    ("Ichalkaranji", 74.4600, 16.7000, "047", "558822"),
    ("Panvel", 73.1000, 18.9900, "048", "669933"),
]

# BuildingType has no "government" value — mixed carries it; the original
# category string is preserved in metadata.
BUILDING_TYPE_MAP = {
    "residential": BuildingType.residential,
    "commercial": BuildingType.commercial,
    "government": BuildingType.mixed,
    "industrial": BuildingType.industrial,
    "infrastructure": BuildingType.infrastructure,
}

# 'workshop'/'public_hall' are not UnitType values — shop/utility carry them.
UNIT_TYPE_MAP = {
    "apartment": UnitType.apartment,
    "parking": UnitType.parking,
    "office": UnitType.office,
    "shop": UnitType.shop,
    "public_hall": UnitType.utility,
    "workshop": UnitType.shop,
    "storage": UnitType.storage,
    "utility": UnitType.utility,
}


def deg_per_m(center_lat):
    return (
        1.0 / 111000.0,
        1.0 / (111000.0 * math.cos(math.radians(center_lat))),
    )


def create_footprint(center_lon, center_lat, width_m, depth_m):
    """Create rectangular footprint in WGS84."""
    deg_lat, deg_lon = deg_per_m(center_lat)
    hw = (width_m / 2.0) * deg_lon
    hd = (depth_m / 2.0) * deg_lat
    return Polygon([
        (center_lon - hw, center_lat - hd),
        (center_lon + hw, center_lat - hd),
        (center_lon + hw, center_lat + hd),
        (center_lon - hw, center_lat + hd),
        (center_lon - hw, center_lat - hd),
    ])


def unit_subdivision(category):
    """Units per floor based on category."""
    return {
        "residential": 4,
        "commercial": 2,
        "government": 3,
        "industrial": 1,  # whole floor
    }.get(category, 2)


def unit_center_offset(unit_idx, units_per_floor, fw, fd, lat):
    """(dLon, dLat, unit_width_m, unit_depth_m) for a unit within its floor."""
    deg_lat, deg_lon = deg_per_m(lat)
    if units_per_floor == 1:
        return 0.0, 0.0, fw, fd
    if units_per_floor == 2:
        side = 1 if unit_idx == 1 else -1
        return side * (fw / 4.0) * deg_lon, 0.0, fw / 2.0, fd
    if units_per_floor == 3:
        return (unit_idx - 2) * (fw / 3.0) * deg_lon, 0.0, fw / 3.0, fd
    # 4 units in a 2x2 grid
    side_x = 1 if unit_idx in (1, 2) else -1
    side_y = 1 if unit_idx in (1, 3) else -1
    return (
        side_x * (fw / 4.0) * deg_lon,
        side_y * (fd / 4.0) * deg_lat,
        fw / 2.0,
        fd / 2.0,
    )


def unit_category_unit_type(category, floor):
    if category == "residential":
        return "apartment" if floor > 1 else "parking"
    if category == "commercial":
        return "office" if floor > 1 else "shop"
    if category == "government":
        return "office" if floor > 1 else "public_hall"
    if category == "industrial":
        return "workshop" if floor == 1 else "storage"
    return "utility"


def seed_government_buildings(db: Session):
    """Seed 25 government/public buildings across Maharashtra."""

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

    owners = []
    for name, otype, contact in PUBLIC_OWNERS:
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

    for btype_idx, (type_name, category, floors, floor_h, color, outline, fw, fd, desc) in enumerate(BUILDING_TYPES):
        loc = LOCATIONS[btype_idx % len(LOCATIONS)]
        location_name, lon, lat, district, village = loc

        parcel_count += 1
        parcel_seq = btype_idx + 1

        parcel_fp = create_footprint(lon, lat, fw + 20, fd + 20)

        p = Parcel(
            parcel_id=uuid.uuid4(),
            ulpin=generate_ulpin(STATE_CODE, district, village, parcel_seq, 0, 0),
            village_code=village,
            geom_2d=WKTElement(f"SRID=4326;{parcel_fp.wkt}", srid=4326),
            area_sqm=round((fw + 20) * (fd + 20), 2),
            parcel_type=ParcelType.multi_storey if floors > 1 else ParcelType.surface,
            status=ParcelStatus.verified,
            metadata_={
                "location_name": location_name,
                "district_code": district,
                "building_type": type_name,
                "category": category,
                "description": desc,
                "cesium_color": color,
                "cesium_outline": outline,
                "width_m": fw,
                "depth_m": fd,
                "total_floors": floors,
                "floor_height_m": floor_h,
            },
            created_by=admin.user_id,
        )
        db.add(p)
        db.flush()

        building_count += 1
        b_fp = create_footprint(lon, lat, fw, fd)
        total_height = floors * floor_h

        b = Building(
            building_id=uuid.uuid4(),
            parcel_id=p.parcel_id,
            building_name=f"{location_name} — {type_name}",
            footprint=WKTElement(f"SRID=4326;{b_fp.wkt}", srid=4326),
            height_m=total_height,
            floors_above_ground=floors,
            floors_below_ground=1 if category in ["commercial", "residential"] else 0,
            construction_year=2005 + (btype_idx % 15),
            building_type=BUILDING_TYPE_MAP[category],
            extracted_by_ml=True,
            confidence_score=0.95,
            metadata_={
                "cesium_color": color,
                "cesium_outline": outline,
                "floor_height_m": floor_h,
                "total_floors": floors,
                "description": desc,
                "category": category,
                "location": location_name,
                "width_m": fw,
                "depth_m": fd,
            },
        )
        db.add(b)
        db.flush()

        units_per_floor = unit_subdivision(category)

        for floor in range(1, floors + 1):
            z_bottom = (floor - 1) * floor_h
            z_top = floor * floor_h

            for unit_idx in range(1, units_per_floor + 1):
                unit_count += 1

                dlon, dlat, uw, ud = unit_center_offset(
                    unit_idx, units_per_floor, fw, fd, lat
                )
                uc_lon = lon + dlon
                uc_lat = lat + dlat
                deg_lat, deg_lon = deg_per_m(lat)
                hw = (uw / 2.0) * deg_lon
                hd = (ud / 2.0) * deg_lat

                # Correctly wound PolyhedralSurfaceZ via the geometry service.
                volume_wkt = box_polyhedral_surface_wkt(
                    uc_lon - hw, uc_lat - hd, uc_lon + hw, uc_lat + hd,
                    z_bottom, z_top,
                )

                unit_ulpin = generate_ulpin(
                    STATE_CODE, district, village, parcel_seq, floor, unit_idx
                )
                unit_type = UNIT_TYPE_MAP[unit_category_unit_type(category, floor)]

                area = round(uw * ud, 2)

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
                    unit_type=unit_type,
                    area_sqm=area,
                    volume_cubm=round(area * floor_h, 2),
                    height_min_m=z_bottom,
                    height_max_m=z_top,
                    status=ParcelStatus.verified,
                    metadata_={
                        "building_name": type_name,
                        "floor_label": f"F{floor:02d}",
                        "unit_index": unit_idx,
                        "cesium_color": color,
                        "location": location_name,
                    },
                )
                db.add(u)
                db.flush()

                owner = owners[unit_count % len(owners)]

                o = OwnershipRecord(
                    ownership_id=uuid.uuid4(),
                    unit_id=u.unit_id,
                    owner_id=owner.owner_id,
                    rights_type=RightsType.full_ownership,  # Government owns all
                    share_percentage=100.0,
                    valid_from=date(2010 + (btype_idx % 10), 1, 1),
                    valid_to=None,
                    registered_by=admin.user_id,
                )
                db.add(o)

        print(f"  ✓ {type_name} at {location_name} — {floors} floors, {units_per_floor} units/floor, color {color}")

    db.commit()

    print()
    print("=" * 60)
    print("GOVERNMENT BUILDINGS SEED COMPLETE")
    print("=" * 60)
    print(f"   Building Types:   {len(BUILDING_TYPES)}")
    print(f"   Parcels:          {parcel_count}")
    print(f"   Buildings:        {building_count}")
    print(f"   Total Units:      {unit_count}")
    print(f"   ULPINs:           {unit_count}")
    print(f"   Public Owners:    {len(owners)}")
    print()
    print("   ALL OWNERS ARE PUBLIC GOVERNMENT ENTITIES")
    print("   NO PRIVATE INDIVIDUALS OR CORPORATIONS")
    print("=" * 60)


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

        seed_government_buildings(db)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()
