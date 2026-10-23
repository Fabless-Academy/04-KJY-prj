from __future__ import annotations
"""Estimate proximity in BEV image coordinates and recommend a speed cap."""

import math
from typing import Any, Dict, List


MAX_RECOMMENDED_SPEED_KMH = 100.0


def calculate_bev_speed_recommendation(
    objects: List[Dict[str, Any]],
    bev_height: int,
    slowdown_y_ratio: float,
    stop_y_ratio: float,
    ego_lane_id: int = 1,
) -> Dict[str, Any]:
    """Return a distance-based speed target using the nearest ego-lane object."""
    if bev_height <= 0:
        raise ValueError("BEV height must be greater than zero")
    if not 0.0 <= slowdown_y_ratio < stop_y_ratio <= 1.0:
        raise ValueError("expected 0 <= slowdown ratio < stop ratio <= 1")

    ego_lane_objects = [
        obj
        for obj in objects
        if obj.get("lane_id") == ego_lane_id
        and isinstance(obj.get("bev_y"), (int, float))
        and math.isfinite(float(obj["bev_y"]))
    ]
    if not ego_lane_objects:
        return {
            "proximity_status": "no_ego_lane_object",
            "closest_object_track_id": None,
            "closest_object_y_ratio": None,
            "recommended_speed_kmh": MAX_RECOMMENDED_SPEED_KMH,
        }

    closest = max(ego_lane_objects, key=lambda obj: float(obj["bev_y"]))
    y_ratio = float(closest["bev_y"]) / float(bev_height)
    if y_ratio <= slowdown_y_ratio:
        recommended_speed = MAX_RECOMMENDED_SPEED_KMH
        status = "clear"
    elif y_ratio >= stop_y_ratio:
        recommended_speed = 0.0
        status = "stop"
    else:
        remaining_ratio = (stop_y_ratio - y_ratio) / (stop_y_ratio - slowdown_y_ratio)
        recommended_speed = MAX_RECOMMENDED_SPEED_KMH * remaining_ratio
        status = "slowing"

    return {
        "proximity_status": status,
        "closest_object_track_id": closest.get("track_id"),
        "closest_object_y_ratio": y_ratio,
        "recommended_speed_kmh": float(recommended_speed),
    }
