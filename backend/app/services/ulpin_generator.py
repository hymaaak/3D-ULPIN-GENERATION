"""Hierarchical 3D ULPIN encoding (Section 7).

Format : 3D-ULPIN-{STATE}-{DISTRICT}-{VILLAGE}-{PARCEL}-F{floor}-U{unit}-{CHECKSUM}
Example: 3D-ULPIN-27-023-456789-0042-F05-U01-XX
"""
from __future__ import annotations

PREFIX = "3D-ULPIN"


def _checksum(base: str) -> str:
    """Modulo-97 checksum over the digit string with F->15, U->21 substitution."""
    digits = base.replace("F", "15").replace("U", "21")
    return str(97 - (int(digits) % 97)).zfill(2)


def generate_ulpin(
    state_code: str,
    district_code: str,
    village_code: str,
    parcel_seq: int,
    floor_num: int,
    unit_num: int,
) -> str:
    base = (
        f"{state_code}{district_code}{village_code}"
        f"{parcel_seq:04d}F{floor_num:02d}U{unit_num:02d}"
    )
    checksum = _checksum(base)
    return (
        f"{PREFIX}-{state_code}-{district_code}-{village_code}"
        f"-{parcel_seq:04d}-F{floor_num:02d}-U{unit_num:02d}-{checksum}"
    )


def parse_ulpin(ulpin: str) -> dict[str, str | int] | None:
    """Split a ULPIN into its segments; None if malformed."""
    if not ulpin.startswith(f"{PREFIX}-"):
        return None
    parts = ulpin[len(PREFIX) + 1 :].split("-")
    if len(parts) != 7:
        return None
    state, district, village, parcel, floor, unit, checksum = parts
    if not (len(state) == 2 and len(district) == 3 and len(village) == 6):
        return None
    if not (len(parcel) == 4 and len(floor) == 3 and len(unit) == 3 and len(checksum) == 2):
        return None
    if not (floor.startswith("F") and unit.startswith("U")):
        return None
    return {
        "state": state,
        "district": district,
        "village": village,
        "parcel": int(parcel),
        "floor": floor,
        "unit": unit,
        "checksum": checksum,
    }


def validate_ulpin(ulpin: str) -> bool:
    parts = parse_ulpin(ulpin)
    if parts is None:
        return False
    base = (
        f"{parts['state']}{parts['district']}{parts['village']}"
        f"{parts['parcel']:04d}{parts['floor']}{parts['unit']}"
    )
    return parts["checksum"] == _checksum(base)
