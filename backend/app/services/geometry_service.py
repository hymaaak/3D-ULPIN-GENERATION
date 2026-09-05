"""3D geometry helpers: PolyhedralSurfaceZ boxes, extrusion, GeoJSON entities."""
from __future__ import annotations

import json
import math
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.utils.geo_utils import deg2_area_to_m2, safe_from_wkt

# Approximate meters per degree latitude; used for mock CRS conversions.
METERS_PER_DEG_LAT = 111320.0


def box_polyhedral_surface_wkt(
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
    zmin: float,
    zmax: float,
) -> str:
    """Emit a valid 6-face POLYHEDRALSURFACE Z WKT (Section 9, Pipeline 3)."""
    # Faces wound counter-clockwise seen from outside the box (right-hand rule),
    # otherwise SFCGAL rejects the shell in ST_Volume/ST_3DIntersection.
    bottom = [
        (minx, miny, zmin), (minx, maxy, zmin),
        (maxx, maxy, zmin), (maxx, miny, zmin), (minx, miny, zmin),
    ]
    top = [
        (minx, miny, zmax), (maxx, miny, zmax),
        (maxx, maxy, zmax), (minx, maxy, zmax), (minx, miny, zmax),
    ]
    south = [
        (minx, miny, zmin), (maxx, miny, zmin),
        (maxx, miny, zmax), (minx, miny, zmax), (minx, miny, zmin),
    ]
    north = [
        (minx, maxy, zmin), (minx, maxy, zmax),
        (maxx, maxy, zmax), (maxx, maxy, zmin), (minx, maxy, zmin),
    ]
    west = [
        (minx, miny, zmin), (minx, miny, zmax),
        (minx, maxy, zmax), (minx, maxy, zmin), (minx, miny, zmin),
    ]
    east = [
        (maxx, miny, zmin), (maxx, maxy, zmin),
        (maxx, maxy, zmax), (maxx, miny, zmax), (maxx, miny, zmin),
    ]
    faces = (bottom, top, south, north, west, east)

    def ring(coords: list[tuple[float, float, float]]) -> str:
        # Each face is a Polygon wrapping the ring, hence double parens:
        # POLYHEDRALSURFACE Z (((x y z, ...)), ((...)), ...)
        return "((" + ", ".join(f"{x} {y} {z}" for x, y, z in coords) + "))"

    return "POLYHEDRALSURFACE Z (" + ", ".join(ring(f) for f in faces) + ")"


def wkt_to_ewkt(wkt: str, srid: int = 4326) -> str:
    if wkt.upper().startswith("SRID="):
        return wkt
    return f"SRID={srid};{wkt}"


def extrude_footprint(
    footprint_wkt: str,
    zmin: float,
    zmax: float,
) -> tuple[str, float, float]:
    """Extrude a 2D footprint polygon to a 3D box volume.

    Returns (polyhedral_surface_z_wkt, area_sqm, volume_cubm).
    """
    geom = safe_from_wkt(footprint_wkt)
    if geom is None or geom.is_empty:
        raise ValueError("Invalid footprint WKT")
    minx, miny, maxx, maxy = geom.bounds
    volume_wkt = box_polyhedral_surface_wkt(minx, miny, maxx, maxy, zmin, zmax)
    lat = (miny + maxy) / 2.0
    area_sqm = deg2_area_to_m2(geom.area, lat)
    volume_cubm = area_sqm * max(zmax - zmin, 0.0)
    return volume_wkt, round(area_sqm, 2), round(volume_cubm, 2)


def subdivide_footprint(
    footprint_wkt: str,
    index: int,
    count: int,
) -> tuple[float, float, float, float]:
    """Split a footprint envelope into `count` vertical slices; return slice bounds."""
    geom = safe_from_wkt(footprint_wkt)
    if geom is None or geom.is_empty:
        raise ValueError("Invalid footprint WKT")
    minx, miny, maxx, maxy = geom.bounds
    width = (maxx - minx) / max(count, 1)
    slice_minx = minx + index * width
    slice_maxx = slice_minx + width
    return slice_minx, miny, slice_maxx, maxy


def split_footprint_polygon(
    footprint_wkt: str,
    index: int,
    count: int,
) -> str:
    """Return the WKT of the `index`-th vertical slice of a footprint envelope."""
    minx, miny, maxx, maxy = subdivide_footprint(footprint_wkt, index, count)
    geom = safe_from_wkt(footprint_wkt)
    box = _box_polygon(minx, miny, maxx, maxy)
    clipped = geom.intersection(box)
    if clipped.is_empty:
        return box.wkt
    return clipped.wkt


def _box_polygon(minx: float, miny: float, maxx: float, maxy: float):
    from shapely.geometry import Polygon

    return Polygon(
        [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy), (minx, miny)]
    )


def meters_to_deg_lon(meters: float, lat: float) -> float:
    cos_lat = math.cos(math.radians(lat))
    if abs(cos_lat) < 1e-6:
        return 0.0
    return meters / (METERS_PER_DEG_LAT * cos_lat)


def meters_to_deg_lat(meters: float) -> float:
    return meters / METERS_PER_DEG_LAT


def parcel_entities_geojson(db: Session, parcel_id) -> dict[str, Any]:
    """Build a Cesium-ready GeoJSON FeatureCollection for a parcel (demo mode).

    Uses PostGIS to serialize footprints and unit volume envelopes.
    """
    parcel_row = db.execute(
        text(
            "SELECT parcel_id, ulpin, status, parcel_type, "
            "ST_AsGeoJSON(geom_2d) AS geom FROM parcels WHERE parcel_id = :pid"
        ),
        {"pid": str(parcel_id)},
    ).mappings().first()

    features: list[dict[str, Any]] = []
    if parcel_row and parcel_row["geom"]:
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(parcel_row["geom"]),
                "properties": {
                    "kind": "parcel",
                    "id": str(parcel_row["parcel_id"]),
                    "ulpin": parcel_row["ulpin"],
                    "status": parcel_row["status"],
                    "parcel_type": parcel_row["parcel_type"],
                },
            }
        )

    buildings = db.execute(
        text(
            "SELECT building_id, building_name, building_type, height_m, "
            "floors_above_ground, confidence_score, ST_AsGeoJSON(footprint) AS geom "
            "FROM buildings WHERE parcel_id = :pid"
        ),
        {"pid": str(parcel_id)},
    ).mappings().all()

    building_ids = [str(b["building_id"]) for b in buildings]
    units: list[Any] = []
    if building_ids:
        units = db.execute(
            text(
                "SELECT u.unit_id, u.unit_ulpin, u.unit_type, u.status, u.floor_number, "
                "u.floor_label, u.height_min_m, u.height_max_m, u.area_sqm, u.volume_cubm, "
                "u.building_id, ST_AsGeoJSON(ST_Envelope(ST_Force2D(u.volume_3d))) AS geom "
                "FROM units u WHERE u.building_id IN :bids"
            ).bindparams(bindparam("bids", expanding=True)),
            {"bids": building_ids},
        ).mappings().all()

    for b in buildings:
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(b["geom"]) if b["geom"] else None,
                "properties": {
                    "kind": "building",
                    "id": str(b["building_id"]),
                    "name": b["building_name"],
                    "building_type": b["building_type"],
                    "height_m": float(b["height_m"]) if b["height_m"] is not None else None,
                    "floors_above_ground": b["floors_above_ground"],
                    "confidence": float(b["confidence_score"]) if b["confidence_score"] is not None else None,
                },
            }
        )

    for u in units:
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(u["geom"]) if u["geom"] else None,
                "properties": {
                    "kind": "unit",
                    "id": str(u["unit_id"]),
                    "building_id": str(u["building_id"]),
                    "unit_ulpin": u["unit_ulpin"],
                    "unit_type": u["unit_type"],
                    "status": u["status"],
                    "floor_number": u["floor_number"],
                    "floor_label": u["floor_label"],
                    "height_min_m": float(u["height_min_m"]) if u["height_min_m"] is not None else None,
                    "height_max_m": float(u["height_max_m"]) if u["height_max_m"] is not None else None,
                    "area_sqm": float(u["area_sqm"]) if u["area_sqm"] is not None else None,
                    "volume_cubm": float(u["volume_cubm"]) if u["volume_cubm"] is not None else None,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "parcel_id": str(parcel_id),
            "demo": True,
            "note": "Cesium entities demo payload; extrude units between height_min_m/height_max_m",
        },
    }
