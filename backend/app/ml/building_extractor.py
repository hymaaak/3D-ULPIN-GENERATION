"""Mock building extraction (Section 9, Pipeline 1; Phase 5 pre-computed mock).

Real pipeline: SAM auto-mask generator over an orthomosaic. This mock returns
realistic footprint polygons with confidence scores, import-safe (Shapely only).
"""
from __future__ import annotations

import random
import time
from typing import Callable

from shapely.geometry import Polygon

ProgressCb = Callable[[int, str], None]

# Demo origin: Mumbai (EPSG:4326)
BASE_LON = 72.8777
BASE_LAT = 19.0760


def extract_buildings(
    count: int = 3,
    seed: int | None = 42,
    progress_cb: ProgressCb | None = None,
) -> list[dict]:
    """Return pre-computed building-like footprints around the demo origin.

    Each result: {footprint: Polygon, footprint_wkt, confidence, area_sqm}
    """
    rng = random.Random(seed)
    results: list[dict] = []
    for i in range(count):
        if progress_cb:
            progress_cb(int(10 + 25 * (i + 1) / count), f"extracting building {i + 1}/{count}")
        time.sleep(0.3)  # simulated inference time
        offset_x = rng.uniform(-0.002, 0.002)
        offset_y = rng.uniform(-0.002, 0.002)
        size = rng.uniform(0.0004, 0.0009)  # ~45-100 m
        lon = BASE_LON + offset_x
        lat = BASE_LAT + offset_y
        poly = Polygon(
            [
                (lon, lat),
                (lon + size, lat),
                (lon + size, lat + size),
                (lon, lat + size),
                (lon, lat),
            ]
        )
        results.append(
            {
                "footprint": poly,
                "footprint_wkt": poly.wkt,
                "confidence": round(rng.uniform(0.82, 0.98), 2),
                "area_sqm": round(size * size * 111320.0**2, 2),
            }
        )
    if progress_cb:
        progress_cb(35, "building extraction complete")
    return results
