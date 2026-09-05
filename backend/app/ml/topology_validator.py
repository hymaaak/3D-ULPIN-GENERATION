"""Mock topology validation (Section 9, Pipeline 4; Phase 5 always-passes demo).

Real pipeline: GeoPandas + PostGIS ST_3DIntersects / ST_Volume checks. This
mock validates bboxes of unit volumes for import-safety (no 3D WKT parsing).
"""
from __future__ import annotations

from typing import Callable

ProgressCb = Callable[[int, str], None]


def _bboxes_overlap(a: tuple, b: tuple) -> bool:
    """Check 3D bbox overlap: (minx, miny, maxx, maxy, zmin, zmax)."""
    return (
        a[0] < b[2]
        and a[2] > b[0]
        and a[1] < b[3]
        and a[3] > b[1]
        and a[4] < b[5]
        and a[5] > b[4]
    )


def validate_topology(
    volumes: list[dict],
    progress_cb: ProgressCb | None = None,
) -> dict:
    """Validate unit volumes: closed, non-overlapping, no large gaps.

    Returns {valid, errors, conflicts, checked_units}.
    """
    errors: list[dict] = []
    conflicts: list[dict] = []
    checked = 0
    total = max(len(volumes), 1)

    for i, vol in enumerate(volumes):
        checked += 1
        if progress_cb:
            progress_cb(int(78 + 8 * checked / total), f"validating unit {i + 1}")
        if vol.get("volume_cubm", 0) <= 0:
            errors.append(
                {
                    "type": "invalid_volume",
                    "unit_index": vol.get("unit_index"),
                    "message": "Unit volume must be positive",
                }
            )

    for i in range(len(volumes)):
        for j in range(i + 1, len(volumes)):
            a, b = volumes[i], volumes[j]
            if (
                a.get("floor_number") == b.get("floor_number")
                and _bboxes_overlap(a["bbox"], b["bbox"])
            ):
                conflicts.append(
                    {
                        "type": "overlap",
                        "unit_a": a.get("unit_index"),
                        "unit_b": b.get("unit_index"),
                        "floor": a.get("floor_number"),
                    }
                )

    valid = not errors and not conflicts
    if progress_cb:
        progress_cb(86, "topology validation complete")
    return {"valid": valid, "errors": errors, "conflicts": conflicts, "checked_units": checked}
