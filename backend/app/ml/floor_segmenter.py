"""Mock floor segmentation (Section 9, Pipeline 2; Phase 5 pre-computed mock).

Real pipeline: RANSAC ground removal + Z-histogram slab peaks + DBSCAN. This
mock returns regular floor z-ranges, import-safe (pure Python).
"""
from __future__ import annotations

import time
from typing import Callable

ProgressCb = Callable[[int, str], None]

FLOOR_HEIGHT_M = 3.0


def segment_floors(
    floors_above_ground: int,
    floors_below_ground: int = 0,
    floor_height_m: float = FLOOR_HEIGHT_M,
    progress_cb: ProgressCb | None = None,
) -> list[dict]:
    """Return per-floor clusters as z-ranges.

    Each result: {floor_number, z_min, z_max, points}
    """
    results: list[dict] = []
    total = floors_above_ground + floors_below_ground
    step = 0
    for floor in range(1, floors_above_ground + 1):
        step += 1
        time.sleep(0.2)  # simulated clustering
        if progress_cb:
            progress_cb(int(40 + 12 * step / max(total, 1)), f"segmenting floor {floor}")
        results.append(
            {
                "floor_number": floor,
                "floor_label": f"F{floor:02d}",
                "z_min": round((floor - 1) * floor_height_m, 2),
                "z_max": round(floor * floor_height_m, 2),
                "points": 15000 + floor * 137,
            }
        )
    for floor in range(1, floors_below_ground + 1):
        step += 1
        if progress_cb:
            progress_cb(int(40 + 12 * step / max(total, 1)), f"segmenting basement {floor}")
        results.append(
            {
                "floor_number": -floor,
                "floor_label": f"B{floor:02d}",
                "z_min": round(-floor * floor_height_m, 2),
                "z_max": round(-(floor - 1) * floor_height_m, 2),
                "points": 9000 + floor * 91,
            }
        )
    if progress_cb:
        progress_cb(52, "floor segmentation complete")
    return results
