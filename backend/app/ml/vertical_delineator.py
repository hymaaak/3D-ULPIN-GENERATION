"""Mock vertical delineation (Section 9, Pipeline 3; Phase 5 simple geometry).

Real pipeline: voxel clustering + alpha shapes over floor plans. This mock
extrudes simple room polygons into 6-face PolyhedralSurfaceZ volumes.
"""
from __future__ import annotations

import time
from typing import Callable

from app.services.geometry_service import (
    extrude_footprint,
    split_footprint_polygon,
)
from app.utils.geo_utils import deg2_area_to_m2, safe_from_wkt

ProgressCb = Callable[[int, str], None]

UNIT_TYPES = ["apartment", "apartment", "shop", "office"]


def delineate_volumes(
    footprint_wkt: str,
    floors: list[dict],
    units_per_floor: int = 2,
    progress_cb: ProgressCb | None = None,
) -> list[dict]:
    """Extrude each floor's slice of the footprint into unit volumes.

    Each result: {unit_index, floor_number, floor_label, volume_wkt, bbox,
                  area_sqm, volume_cubm, z_min, z_max, unit_type}
    """
    results: list[dict] = []
    base_geom = safe_from_wkt(footprint_wkt)
    if base_geom is None or base_geom.is_empty:
        return results
    total = max(len(floors) * units_per_floor, 1)
    done = 0

    for floor in floors:
        for idx in range(units_per_floor):
            done += 1
            time.sleep(0.1)  # simulated voxel clustering
            if progress_cb:
                progress_cb(
                    int(55 + 18 * done / total),
                    f"delineating {floor['floor_label']} unit {idx + 1}",
                )
            slice_wkt = split_footprint_polygon(footprint_wkt, idx, units_per_floor)
            slice_geom = safe_from_wkt(slice_wkt)
            sminx, sminy, smaxx, smaxy = slice_geom.bounds
            zmin = floor["z_min"]
            zmax = floor["z_max"]
            volume_wkt, area_sqm, volume_cubm = extrude_footprint(slice_wkt, zmin, zmax)
            results.append(
                {
                    "unit_index": idx + 1,
                    "floor_number": floor["floor_number"],
                    "floor_label": floor["floor_label"],
                    "volume_wkt": volume_wkt,
                    "bbox": (sminx, sminy, smaxx, smaxy, zmin, zmax),
                    "area_sqm": area_sqm,
                    "volume_cubm": volume_cubm,
                    "z_min": zmin,
                    "z_max": zmax,
                    "unit_type": UNIT_TYPES[(idx + floor["floor_number"]) % len(UNIT_TYPES)],
                }
            )
    if progress_cb:
        progress_cb(73, "vertical delineation complete")
    return results


def footprint_area_sqm(footprint_wkt: str) -> float:
    geom = safe_from_wkt(footprint_wkt)
    if geom is None:
        return 0.0
    minx, miny, maxx, maxy = geom.bounds
    return deg2_area_to_m2(geom.area, (miny + maxy) / 2.0)
