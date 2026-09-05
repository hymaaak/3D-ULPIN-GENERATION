"""
maharashtra_industrial_seed_data.py
Seed script using the original industrial steel fabrication workshop shed
architecture (CROSS SECTION CO) for all buildings across Maharashtra locations.

Run: docker compose exec backend python -m app.utils.maharashtra_industrial_seed_data
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

# ============================================================
# INDUSTRIAL SHED ARCHITECTURE PARAMETERS (from CROSS SECTION CO)
# ============================================================
SHED_PARAMS = {
    "span_m": 24.0,            # Clear span
    "length_m": 60.0,          # Shed length
    "eave_height_m": 6.0,      # Eave height
    "ridge_height_m": 9.0,     # Ridge height (gable roof)
    "bay_width_m": 6.0,        # Bay spacing
    "num_bays": 10,            # 60m / 6m = 10 bays
    "column_grid_m": 6.0,      # Column spacing
    "roof_slope_deg": 15.0,    # Roof slope
    "mezzanine_height_m": 3.5,  # Office/mezzanine floor height
    "plinth_height_m": 0.5,    # Plinth above ground
    "floor_load_kn_m2": 5.0,   # Floor load capacity
}

# Real Maharashtra industrial locations
MAHARASHTRA_INDUSTRIAL_LOCATIONS = [
    ("Nagpur Industrial Area", 79.0882, 21.1458, "026", "987654"),
    ("Pune Chakan MIDC", 73.8567, 18.6804, "024", "123457"),
    ("Nashik Sinnar MIDC", 73.7898, 19.9975, "025", "654322"),
    ("Aurangabad Shendra MIDC", 75.3433, 19.8762, "029", "555667"),
    ("Thane Wagle MIDC", 72.9758, 19.2183, "027", "111223"),
    ("Kalyan Ambernath MIDC", 73.1302, 19.2403, "028", "333445"),
    ("Solapur North MIDC", 75.9064, 17.6599, "030", "777889"),
    ("Kolhapur Five Star MIDC", 74.2436, 16.7050, "032", "112234"),
    ("Sangli Miraj MIDC", 74.6040, 16.8602, "033", "445567"),
    ("Jalgaon MIDC", 75.5626, 21.0077, "034", "778900"),
    ("Akola MIDC", 77.0085, 20.7096, "035", "223345"),
    ("Latur MIDC", 76.5604, 18.4088, "036", "556678"),
    ("Dhule MIDC", 74.7749, 20.9042, "037", "889901"),
    ("Ahmednagar MIDC", 74.7496, 19.0948, "038", "334456"),
    ("Chandrapur Tadali MIDC", 79.2961, 19.9615, "039", "667789"),
    ("Parbhani MIDC", 76.7767, 19.2608, "040", "990012"),
    ("Jalna MIDC", 75.8800, 19.8410, "041", "224467"),
    ("Bhusawal MIDC", 75.8013, 21.0455, "042", "557734"),
    ("Amravati Nandgaon Peth MIDC", 77.7523, 20.9320, "031", "999001"),
    ("Ratnagiri Lote MIDC", 73.3000, 17.0000, "043", "113355"),
]

STATE_CODE = "27"


# ============================================================
# 3D GEOMETRY HELPERS
# ============================================================

def deg_per_m(center_lat):
    return (
        1.0 / 111000.0,
        1.0 / (111000.0 * math.cos(math.radians(center_lat))),
    )


def create_shed_footprint(center_lon, center_lat, length_m, span_m):
    """Create rectangular shed footprint in WGS84."""
    deg_lat, deg_lon = deg_per_m(center_lat)
    half_len_lon = (length_m / 2.0) * deg_lon
    half_span_lat = (span_m / 2.0) * deg_lat
    return Polygon([
        (center_lon - half_len_lon, center_lat - half_span_lat),
        (center_lon + half_len_lon, center_lat - half_span_lat),
        (center_lon + half_len_lon, center_lat + half_span_lat),
        (center_lon - half_len_lon, center_lat + half_span_lat),
        (center_lon - half_len_lon, center_lat - half_span_lat),
    ])


def shed_volume_wkt(center_lon, center_lat, params):
    """Main shed body (plinth to eave) as a correctly wound PolyhedralSurfaceZ."""
    deg_lat, deg_lon = deg_per_m(center_lat)
    hx = (params["length_m"] / 2.0) * deg_lon
    hy = (params["span_m"] / 2.0) * deg_lat
    return box_polyhedral_surface_wkt(
        center_lon - hx, center_lat - hy, center_lon + hx, center_lat + hy,
        params["plinth_height_m"], params["eave_height_m"],
    )


def create_unit_3d_volume_wkt(center_lon, center_lat, bay_idx, num_bays, params, floor, unit):
    """
    3D volume for a single bay unit (left/right half of one bay), as a
    correctly wound PolyhedralSurfaceZ box. Each bay gets its own volumetric
    ULPIN.
    """
    deg_lat, deg_lon = deg_per_m(center_lat)
    L = params["length_m"]
    S = params["span_m"]
    bay_L = L / num_bays

    hx1 = (-L / 2 + bay_idx * bay_L) * deg_lon
    hx2 = (-L / 2 + (bay_idx + 1) * bay_L) * deg_lon
    hy = (S / 2.0) * deg_lat

    if floor == 0:  # Ground floor
        z_bottom = params["plinth_height_m"]
        z_top = params["mezzanine_height_m"]
    elif floor == 1:  # Mezzanine
        z_bottom = params["mezzanine_height_m"]
        z_top = params["eave_height_m"]
    else:  # Roof space (air right)
        z_bottom = params["eave_height_m"]
        z_top = params["eave_height_m"] + 3.0

    hy1, hy2 = (-hy, 0.0) if unit == 1 else (0.0, hy)

    return box_polyhedral_surface_wkt(
        center_lon + hx1, center_lat + hy1, center_lon + hx2, center_lat + hy2,
        z_bottom, z_top,
    )


# ============================================================
# OWNERS
# ============================================================
INDUSTRIAL_OWNERS = [
    ("Tata Steel Fabrication Ltd", "corporation", {"phone": "+91-22-12345678", "address": "Mumbai", "gst": "27AABCT1234C1Z5"}),
    ("Maharashtra State Industrial Corp", "government", {"phone": "+91-22-87654321", "address": "Mumbai", "department": "MIDC"}),
    ("Patel Engineering Works", "individual", {"phone": "+91-9876543210", "address": "Nagpur"}),
    ("Reliance Industrial Infrastructure", "corporation", {"phone": "+91-22-99998888", "address": "Navi Mumbai"}),
    ("Sharma & Sons Fabricators", "individual", {"phone": "+91-9876543211", "address": "Pune"}),
    ("Bharat Heavy Plate Ltd", "corporation", {"phone": "+91-253-1234567", "address": "Nashik"}),
    ("Aurangabad Tool Room", "government", {"phone": "+91-240-1234567", "address": "Aurangabad"}),
    ("Kulkarni Structural Steel", "individual", {"phone": "+91-9876543212", "address": "Kolhapur"}),
    ("JSW Steel Processing", "corporation", {"phone": "+91-22-77776666", "address": "Dolvi"}),
    ("Solapur Engineering Cluster", "corporation", {"phone": "+91-217-1234567", "address": "Solapur"}),
    ("Jindal Saw Ltd", "corporation", {"phone": "+91-257-1234567", "address": "Jalgaon"}),
    ("L&T Fabrication Division", "corporation", {"phone": "+91-22-55554444", "address": "Powai, Mumbai"}),
    ("SAIL Maharashtra Depot", "government", {"phone": "+91-724-1234567", "address": "Akola"}),
    ("Godrej Industrial Equipment", "corporation", {"phone": "+91-22-33332222", "address": "Vikhroli, Mumbai"}),
    ("Vasudev Steel Traders", "individual", {"phone": "+91-9876543213", "address": "Thane"}),
    ("Mahindra Heavy Engines", "corporation", {"phone": "+91-20-12345678", "address": "Pune"}),
    ("Nitin Castings Ltd", "corporation", {"phone": "+91-231-1234567", "address": "Kolhapur"}),
    ("Chandrapur Ferro Alloys", "corporation", {"phone": "+91-7172-123456", "address": "Chandrapur"}),
    ("Ratnagiri Marine Fabricators", "corporation", {"phone": "+91-2352-123456", "address": "Ratnagiri"}),
    ("Amravati Agro Implements", "individual", {"phone": "+91-9876543214", "address": "Amravati"}),
]


def seed_industrial_maharashtra(db: Session):
    """Seed industrial shed data across Maharashtra using CROSS SECTION CO architecture."""

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
    for name, otype, contact in INDUSTRIAL_OWNERS:
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

    for loc_idx, (location_name, lon, lat, district, village) in enumerate(MAHARASHTRA_INDUSTRIAL_LOCATIONS):
        # 1 parcel per location
        parcel_count += 1
        parcel_seq = loc_idx + 1

        parcel_footprint = create_shed_footprint(
            lon, lat,
            SHED_PARAMS["length_m"] + 20,
            SHED_PARAMS["span_m"] + 20,
        )

        p = Parcel(
            parcel_id=uuid.uuid4(),
            ulpin=generate_ulpin(STATE_CODE, district, village, parcel_seq, 0, 0),
            village_code=village,
            geom_2d=WKTElement(f"SRID=4326;{parcel_footprint.wkt}", srid=4326),
            area_sqm=round((SHED_PARAMS["length_m"] + 20) * (SHED_PARAMS["span_m"] + 20), 2),
            # No 'industrial' value exists in the parcel_type enum — 'mixed'
            # carries it; the industrial flag lives in metadata.
            parcel_type=ParcelType.mixed,
            status=ParcelStatus.verified,
            metadata_={
                "location_name": location_name,
                "district_code": district,
                "industrial_zone": True,
                "shed_type": "steel_fabrication_workshop",
                "cross_section": "CO",
            },
            created_by=admin.user_id,
        )
        db.add(p)
        db.flush()

        # 2 sheds per parcel (offset ~330 m east / ~110 m north: no overlap)
        for b_idx in range(2):
            building_count += 1
            offset_lon = lon + (b_idx * 0.003)
            offset_lat = lat + (b_idx * 0.001)

            shed_footprint = create_shed_footprint(
                offset_lon, offset_lat,
                SHED_PARAMS["length_m"],
                SHED_PARAMS["span_m"],
            )

            b = Building(
                building_id=uuid.uuid4(),
                parcel_id=p.parcel_id,
                building_name=f"{location_name} Shed {b_idx + 1}",
                footprint=WKTElement(f"SRID=4326;{shed_footprint.wkt}", srid=4326),
                height_m=SHED_PARAMS["ridge_height_m"],
                floors_above_ground=2,  # Ground + Mezzanine
                floors_below_ground=0,
                construction_year=2015 + (loc_idx % 8),
                building_type=BuildingType.industrial,
                extracted_by_ml=True,
                confidence_score=0.94,
                metadata_={
                    "shed_params": SHED_PARAMS,
                    "cross_section_detail": "CO",
                    **{k: SHED_PARAMS[k] for k in (
                        "span_m", "length_m", "eave_height_m", "ridge_height_m",
                        "num_bays", "bay_width_m", "column_grid_m", "roof_slope_deg",
                        "mezzanine_height_m", "plinth_height_m", "floor_load_kn_m2",
                    )},
                },
            )
            db.add(b)
            db.flush()

            num_bays = SHED_PARAMS["num_bays"]

            for bay in range(num_bays):
                for floor in range(2):  # Ground (0) and Mezzanine (1)
                    for half in range(2):  # Left (0) / Right (1) half of bay
                        unit_count += 1

                        floor_label = "GF" if floor == 0 else "MF"
                        # 'workshop' is not a unit_type enum value — shop carries it,
                        # the label keeps the workshop semantics.
                        unit_type = UnitType.shop if floor == 0 else UnitType.office

                        # Unit number encodes (shed, floor, half): 1-8 =
                        # shed 1-2 x (Ground, Mezzanine) x (Left, Right), so
                        # every (bay, shed, floor, half) gets a unique ULPIN.
                        unit_seq = b_idx * 4 + floor * 2 + half + 1
                        unit_ulpin = generate_ulpin(
                            STATE_CODE, district, village, parcel_seq, bay + 1, unit_seq
                        )

                        volume_3d_wkt = create_unit_3d_volume_wkt(
                            offset_lon, offset_lat, bay, num_bays, SHED_PARAMS, floor, half + 1
                        )

                        if floor == 0:
                            z_bottom = SHED_PARAMS["plinth_height_m"]
                            z_top = SHED_PARAMS["mezzanine_height_m"]
                        else:
                            z_bottom = SHED_PARAMS["mezzanine_height_m"]
                            z_top = SHED_PARAMS["eave_height_m"]

                        bay_area = SHED_PARAMS["bay_width_m"] * (SHED_PARAMS["span_m"] / 2)

                        u = Unit(
                            unit_id=uuid.uuid4(),
                            building_id=b.building_id,
                            parent_parcel_id=p.parcel_id,
                            unit_ulpin=unit_ulpin,
                            volume_3d=WKTElement(
                                f"SRID=4326;{volume_3d_wkt}", srid=4326, extended=True
                            ),
                            floor_number=bay + 1,  # Bay number as floor for industrial layout
                            floor_label=f"Bay{bay + 1}-{floor_label}-{chr(65 + half)}",
                            unit_type=unit_type,
                            area_sqm=round(bay_area, 2),
                            volume_cubm=round(bay_area * (z_top - z_bottom), 2),
                            height_min_m=z_bottom,
                            height_max_m=z_top,
                            status=ParcelStatus.verified,
                            metadata_={
                                "bay_number": bay + 1,
                                "bay_width_m": SHED_PARAMS["bay_width_m"],
                                "half": "left" if half == 0 else "right",
                                "floor_type": "ground" if floor == 0 else "mezzanine",
                                "shed_cross_section": "CO",
                                "workshop": floor == 0,
                            },
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
                            valid_from=date(2018 + (loc_idx % 5), 1, 1),
                            valid_to=None,
                            registered_by=admin.user_id,
                        )
                        db.add(o)

    db.commit()

    print("=" * 60)
    print("INDUSTRIAL MAHARASHTRA SEED COMPLETE")
    print("=" * 60)
    print(f"   Locations:         {len(MAHARASHTRA_INDUSTRIAL_LOCATIONS)}")
    print(f"   Parcels:           {parcel_count}")
    print(f"   Buildings (Sheds): {building_count}")
    print(f"   Bays per shed:     {SHED_PARAMS['num_bays']}")
    print(f"   Floors per bay:    2 (Ground + Mezzanine)")
    print(f"   Halves per bay:    2 (Left + Right)")
    print(f"   Total Units:       {unit_count}")
    print(f"   ULPINs Generated:  {unit_count}")
    print(f"   Owners:            {len(owners)}")
    print()
    print("   Architecture:      Steel Fabrication Workshop")
    print("   Cross Section:     CO")
    print(f"   Span:              {SHED_PARAMS['span_m']}m")
    print(f"   Length:            {SHED_PARAMS['length_m']}m")
    print(f"   Eave Height:       {SHED_PARAMS['eave_height_m']}m")
    print(f"   Ridge Height:      {SHED_PARAMS['ridge_height_m']}m")
    print(f"   Bay Width:         {SHED_PARAMS['bay_width_m']}m")
    print(f"   Num Bays:          {SHED_PARAMS['num_bays']}")
    print(f"   Roof Slope:        {SHED_PARAMS['roof_slope_deg']} deg")
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

        seed_industrial_maharashtra(db)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()
