"""Custom validators for geometry, ULPIN and common input checks."""
from __future__ import annotations

import re
from datetime import date

from app.services.ulpin_generator import validate_ulpin as _validate_ulpin

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value or ""))


def is_valid_geometry_wkt(wkt: str | None) -> bool:
    """True when the WKT parses with Shapely (2D geometries only)."""
    if not wkt:
        return True  # optional geometry
    from app.utils.geo_utils import safe_from_wkt

    geom = safe_from_wkt(wkt)
    return geom is not None and not geom.is_empty


def is_valid_ulpin(ulpin: str) -> bool:
    return _validate_ulpin(ulpin)


def is_valid_date_range(valid_from: date, valid_to: date | None) -> bool:
    return valid_to is None or valid_to > valid_from
