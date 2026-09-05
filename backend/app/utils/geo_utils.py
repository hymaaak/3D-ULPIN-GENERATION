"""CRS, WKT and bbox helpers (EPSG:4326-centric, mock-friendly)."""
from __future__ import annotations

import math
import re
from typing import Any

METERS_PER_DEG_LAT = 111320.0

_SRID_RE = re.compile(r"^\s*SRID\s*=\s*\d+\s*;", re.IGNORECASE)


def strip_srid(wkt: str) -> str:
    """Remove an EWKT 'SRID=xxxx;' prefix if present."""
    return _SRID_RE.sub("", wkt).strip()


def safe_from_wkt(wkt: str | None):
    """Parse WKT (tolerates EWKT prefixes); None on failure."""
    if not wkt:
        return None
    try:
        from shapely import from_wkt

        return from_wkt(strip_srid(wkt))
    except Exception:
        return None


def geom_to_wkt(geom: Any) -> str | None:
    """Convert GeoAlchemy2 WKBElement / shapely geom / str to a WKT string."""
    if geom is None:
        return None
    if isinstance(geom, str):
        return geom
    try:
        from geoalchemy2.elements import WKBElement
        from geoalchemy2.shape import to_shape

        if isinstance(geom, WKBElement):
            return to_shape(geom).wkt
    except Exception:
        pass
    wkt = getattr(geom, "wkt", None)
    return wkt if wkt is not None else str(geom)


def model_to_dict(obj: Any, geom_fields: tuple[str, ...] = ()) -> dict:
    """Serialize an ORM row to a dict, converting geometry columns to WKT.

    Column names are resolved through the mapper, so columns shadowed by
    declarative internals (e.g. `metadata` -> attribute `metadata_`) serialize
    from the mapped attribute, not the MetaData object.
    """
    from sqlalchemy import inspect as sa_inspect

    mapper = sa_inspect(obj.__class__)
    data: dict[str, Any] = {}
    for column in obj.__table__.columns:
        attr = mapper.get_property_by_column(column).key
        value = getattr(obj, attr)
        if column.name in geom_fields:
            value = geom_to_wkt(value)
        data[column.name] = value
    return data


def deg2_area_to_m2(area_deg2: float, lat: float) -> float:
    """Roughly convert square degrees to square meters at a given latitude."""
    return area_deg2 * (METERS_PER_DEG_LAT ** 2) * math.cos(math.radians(lat))


def meters_to_deg_lat(meters: float) -> float:
    return meters / METERS_PER_DEG_LAT


def meters_to_deg_lon(meters: float, lat: float) -> float:
    cos_lat = math.cos(math.radians(lat))
    if abs(cos_lat) < 1e-6:
        return 0.0
    return meters / (METERS_PER_DEG_LAT * cos_lat)


def offset_point(lon: float, lat: float, dx_m: float, dy_m: float) -> tuple[float, float]:
    """Tiny local EPSG:4326 offset in meters (mock CRS transform)."""
    return lon + meters_to_deg_lon(dx_m, lat), lat + meters_to_deg_lat(dy_m)


def polygon_wkt(coords: list[tuple[float, float]]) -> str:
    from shapely.geometry import Polygon

    return Polygon(coords).wkt
