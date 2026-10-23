from __future__ import annotations
"""차선과 객체 결과를 Qt가 소비하는 payload 구조로 변환하는 모듈."""

from typing import Any, Dict, List, Optional

import numpy as np

from .geometry import (
    BevCorrection,
    build_centerline,
    compute_pure_pursuit_steering,
    fit_lane_set,
    transform_object_foot,
    transform_points,
)
from .state import BevLaneState


def _lane_bottom_x(points: List[Dict[str, int]]) -> Optional[float]:
    """차선의 하단부 x 위치를 대표값으로 계산한다."""
    if not points:
        return None
    ordered = sorted(points, key=lambda p: float(p.get("y", 0)), reverse=True)
    sample = ordered[: min(3, len(ordered))]
    if not sample:
        return None
    return float(np.mean([float(p.get("x", 0)) for p in sample]))


def _interp_lane_x(points: List[Dict[str, int]], target_y: float) -> Optional[float]:
    """차선 point 목록에서 특정 y 위치의 x를 선형 보간한다."""
    if len(points) < 2:
        return None
    ordered = sorted(points, key=lambda p: float(p.get("y", 0)))
    for idx in range(len(ordered) - 1):
        p0 = ordered[idx]
        p1 = ordered[idx + 1]
        y0 = float(p0.get("y", 0))
        y1 = float(p1.get("y", 0))
        if abs(y1 - y0) < 1e-6:
            continue
        low = min(y0, y1)
        high = max(y0, y1)
        if low <= target_y <= high:
            t = (target_y - y0) / (y1 - y0)
            x0 = float(p0.get("x", 0))
            x1 = float(p1.get("x", 0))
            return x0 + (x1 - x0) * t
    return None


def _assign_object_lane_id(
    obj: Dict[str, Any],
    qt_lanes: List[List[Dict[str, int]]],
) -> Optional[int]:
    """BEV 객체가 어느 lane corridor 안에 있는지 판정한다."""
    obj_y = float(obj.get("bev_y", 0.0))
    lane_xs = [_interp_lane_x(lane, obj_y) for lane in qt_lanes[:4]]

    # corridor 0: lane0-lane1, corridor 1: lane1-lane2, corridor 2: lane2-lane3
    corridors = [
        (lane_xs[0], lane_xs[1], 0),
        (lane_xs[1], lane_xs[2], 1),
        (lane_xs[2], lane_xs[3], 2),
    ]
    obj_x = float(obj.get("bev_x", 0.0))
    for left_x, right_x, lane_id in corridors:
        if left_x is None or right_x is None:
            continue
        low = min(left_x, right_x)
        high = max(left_x, right_x)
        if low <= obj_x <= high:
            return lane_id

    return None


def _normalize_lane_slots(
    lanes_in: List[Dict[str, Any]],
    homography: np.ndarray,
    payload_width: int,
    payload_height: int,
    source_width: int,
    source_height: int,
    correction: Optional[BevCorrection],
    bev_width: int,
    lane_state: Optional[BevLaneState],
) -> List[List[Dict[str, int]]]:
    """입력 차선들을 좌->우 순서의 4개 고정 슬롯으로 정규화한다."""
    transformed: List[Dict[str, Any]] = []
    for lane in lanes_in:
        points = transform_points(
            lane.get("points", []) or [],
            homography,
            payload_width,
            payload_height,
            source_width,
            source_height,
            correction,
        )
        bottom_x = _lane_bottom_x(points)
        if not points or bottom_x is None:
            continue
        transformed.append(
            {
                "points": points,
                "bottom_x": float(bottom_x),
                "score": float(lane.get("score", lane.get("lane_score", 0.0))),
            }
        )

    transformed.sort(key=lambda lane: lane["bottom_x"])
    slots: List[List[Dict[str, int]]] = [[], [], [], []]
    if not transformed:
        return slots

    if len(transformed) == 1:
        center = float(bev_width) * 0.5
        slots[1 if transformed[0]["bottom_x"] <= center else 2] = list(transformed[0]["points"])
        return slots

    center = float(bev_width) * 0.5
    state_valid = False
    state_center = center
    if lane_state is not None:
        state_valid, state_center = lane_state.get_ego_pair_center()
    # 차량 중심과 가장 잘 맞는 차선 쌍을 ego lane으로 선택한다.
    ego_pair_idx = 0
    best_pair_cost = float("inf")
    for idx in range(len(transformed) - 1):
        left = transformed[idx]
        right = transformed[idx + 1]
        pair_mid = 0.5 * (left["bottom_x"] + right["bottom_x"])
        pair_gap = abs(right["bottom_x"] - left["bottom_x"])
        cost = abs(pair_mid - center) + 0.08 * abs(pair_gap - float(bev_width) * 0.22)
        if state_valid:
            cost += 0.65 * abs(pair_mid - state_center)
        if cost < best_pair_cost:
            best_pair_cost = cost
            ego_pair_idx = idx

    selected_center = 0.5 * (
        transformed[ego_pair_idx]["bottom_x"] + transformed[ego_pair_idx + 1]["bottom_x"]
    )
    if lane_state is not None:
        lane_state.update_ego_pair_center(selected_center)

    slots[1] = list(transformed[ego_pair_idx]["points"])
    slots[2] = list(transformed[ego_pair_idx + 1]["points"])
    if ego_pair_idx - 1 >= 0:
        slots[0] = list(transformed[ego_pair_idx - 1]["points"])
    if ego_pair_idx + 2 < len(transformed):
        slots[3] = list(transformed[ego_pair_idx + 2]["points"])
    return slots


def compute_lane_model(
    left_lane: List[Dict[str, int]],
    right_lane: List[Dict[str, int]],
    bev_width: int,
    bev_height: int,
) -> Dict[str, Any]:
    """좌우 ego 차선으로부터 중심 오프셋, 헤딩, 곡률 근사값을 계산한다."""
    centerline = build_centerline(left_lane, right_lane)
    if len(centerline) < 3:
        return {"valid": False}

    ego_y = float(bev_height) * 0.97
    ego_center_x = float(bev_width) * 0.5
    lane_widths = [abs(float(left["x"]) - float(right["x"])) for left, right in zip(left_lane, right_lane)]
    lane_width_px = float(np.mean(lane_widths)) if lane_widths else float(bev_width) * 0.22

    samples = []
    for point in centerline:
        s = (ego_y - float(point["y"])) / max(float(bev_height), 1.0)
        if s < -0.05:
            continue
        samples.append((s, float(point["x"])))
    if len(samples) < 3:
        return {"valid": False}

    s_vals = np.array([sample[0] for sample in samples], dtype=np.float32)
    x_vals = np.array([sample[1] for sample in samples], dtype=np.float32)
    try:
        coeffs = np.polyfit(s_vals, x_vals, 2)
    except (np.linalg.LinAlgError, ValueError):
        return {"valid": False}

    center_at_ego = float(np.polyval(coeffs, 0.0))
    return {
        "valid": True,
        "lane_width_px": lane_width_px,
        "center_offset_px": center_at_ego - ego_center_x,
        "heading_gain": float(coeffs[1]),
        "curvature_gain": float(coeffs[0]),
        "ego_y_px": ego_y,
    }


def build_lane_payload(
    result: Dict[str, Any],
    homography: np.ndarray,
    bev_width: int,
    bev_height: int,
    source_width: int,
    source_height: int,
    correction: Optional[BevCorrection],
    lane_fit_degree: int,
    lane_fit_samples: int,
    lane_fit_min_points: int,
    lane_top_ratio: float,
    lane_bottom_ratio: float,
    lane_state: Optional[BevLaneState],
    lane_smoothing: float,
) -> List[List[Dict[str, int]]]:
    """result JSON의 lane 목록을 Qt용 4슬롯 차선 payload로 변환한다."""
    payload_width = int(result.get("width", 800))
    payload_height = int(result.get("height", 480))
    lanes_in = result.get("lanes", []) or []
    lanes = _normalize_lane_slots(
        lanes_in,
        homography,
        payload_width,
        payload_height,
        source_width,
        source_height,
        correction,
        bev_width,
        lane_state,
    )

    if lane_fit_degree > 0:
        # 시각화와 path 계산이 안정되도록 lane polyline을 매끈하게 다시 샘플링한다.
        bev_top_y = float(bev_height) * lane_top_ratio
        bev_bottom_y = float(bev_height) * lane_bottom_ratio
        lanes = fit_lane_set(
            lanes,
            lane_fit_degree,
            lane_fit_samples,
            lane_fit_min_points,
            bev_top_y,
            bev_bottom_y,
        )

    if lane_state is not None:
        lanes = lane_state.smooth(lanes, lane_smoothing)
    return [list(lane) for lane in lanes[:4]]


def _build_control_payload(
    qt_lanes: List[List[Dict[str, int]]],
    bev_width: int,
    bev_height: int,
    lane_state: Optional[BevLaneState],
    steering_smoothing: float,
    pp_lookahead_ratio: float,
    pp_wheelbase_ratio: float,
    pp_ego_x_ratio: float,
    pp_ego_y_ratio: float,
    pp_max_steer_deg: float,
) -> Dict[str, Any]:
    """legacy bridge가 사용하던 steering, centerline, lookahead 묶음을 만든다."""
    steering_deg, centerline, lookahead_point = compute_pure_pursuit_steering(
        qt_lanes[1],
        qt_lanes[2],
        bev_width,
        bev_height,
        pp_lookahead_ratio,
        pp_wheelbase_ratio,
        pp_ego_x_ratio,
        pp_ego_y_ratio,
        pp_max_steer_deg,
    )
    if lane_state is not None:
        steering_deg = lane_state.smooth_steering(steering_deg, steering_smoothing)
    return {
        "steering": float(steering_deg),
        "centerline": centerline,
        "lookahead_point": lookahead_point if lookahead_point is not None else {},
        "lane_model": compute_lane_model(qt_lanes[1], qt_lanes[2], bev_width, bev_height),
    }


def build_object_payload(
    result: Dict[str, Any],
    homography: np.ndarray,
    bev_width: int,
    bev_height: int,
    source_width: int,
    source_height: int,
    correction: Optional[BevCorrection],
    include_objects: bool,
    max_objects: int,
    lane_state: Optional[BevLaneState],
    object_track_distance: float,
    object_track_confirm: int,
    object_track_miss: int,
    object_track_alpha: float,
    qt_lanes: List[List[Dict[str, int]]],
) -> Dict[str, Any]:
    """객체 목록을 BEV로 변환하고 lane 상태까지 포함한 payload를 만든다."""
    if not include_objects:
        return {
            "objects": [],
            "bev_objects": [],
            "lane_status": [False, False, False, False, False],
        }

    objects: List[Dict[str, Any]] = list(result.get("objects", []) or [])
    if max_objects > 0:
        objects = objects[:max_objects]

    # 객체는 bbox 하단 중심점만 사용해 BEV 위치로 옮긴다.
    bev_objects = [
        transform_object_foot(obj, homography, int(result.get("width", 800)), int(result.get("height", 480)), source_width, source_height, correction)
        for obj in objects
    ]
    if lane_state is not None:
        bev_objects = lane_state.update_object_tracks(
            bev_objects,
            object_track_distance,
            object_track_confirm,
            object_track_miss,
            object_track_alpha,
            max_objects,
        )
    for obj in bev_objects:
        lane_id = _assign_object_lane_id(obj, qt_lanes)
        obj["lane_id"] = lane_id

    # 5분할 lane status는 기존 Qt indicator와의 호환성을 위해 유지한다.
    lane_status = [False, False, False, False, False]
    for obj in bev_objects:
        center_x = float(obj.get("bev_x", 0.0))
        lane_index = int(center_x * 5.0 / max(bev_width, 1))
        lane_status[max(0, min(4, lane_index))] = True

    return {
        "objects": objects,
        "bev_objects": bev_objects,
        "lane_status": lane_status,
    }


def build_bev_payload(
    result: Dict[str, Any],
    homography: np.ndarray,
    bev_width: int,
    bev_height: int,
    source_width: int,
    source_height: int,
    include_objects: bool,
    max_objects: int,
    correction: Optional[BevCorrection] = None,
    lane_fit_degree: int = 2,
    lane_fit_samples: int = 24,
    lane_fit_min_points: int = 4,
    lane_top_ratio: float = 0.12,
    lane_bottom_ratio: float = 0.97,
    lane_state: Optional[BevLaneState] = None,
    lane_smoothing: float = 0.7,
    steering_smoothing: float = 0.75,
    pp_lookahead_ratio: float = 0.58,
    pp_wheelbase_ratio: float = 0.12,
    pp_ego_x_ratio: float = 0.5,
    pp_ego_y_ratio: float = 0.97,
    pp_max_steer_deg: float = 35.0,
    object_track_distance: float = 60.0,
    object_track_confirm: int = 2,
    object_track_miss: int = 4,
    object_track_alpha: float = 0.7,
) -> Dict[str, Any]:
    """기존 bridge 스크립트 호환용 통합 BEV payload 생성 함수."""
    qt_lanes = build_lane_payload(
        result,
        homography,
        bev_width,
        bev_height,
        source_width,
        source_height,
        correction,
        lane_fit_degree,
        lane_fit_samples,
        lane_fit_min_points,
        lane_top_ratio,
        lane_bottom_ratio,
        lane_state,
        lane_smoothing,
    )
    control = _build_control_payload(
        qt_lanes,
        bev_width,
        bev_height,
        lane_state,
        steering_smoothing,
        pp_lookahead_ratio,
        pp_wheelbase_ratio,
        pp_ego_x_ratio,
        pp_ego_y_ratio,
        pp_max_steer_deg,
    )

    perf = result.get("perf", {}) or {}
    payload: Dict[str, Any] = {
        "frame_index": int(result.get("frame_index", 0)),
        "width": bev_width,
        "height": bev_height,
        "lanes": qt_lanes,
        "bev_width": bev_width,
        "bev_height": bev_height,
        "bev_lanes": qt_lanes,
        "perf": {
            "fps": float(perf.get("fps", 0.0)),
            "cpu": int(perf.get("cpu", 0)),
            "mem": int(perf.get("mem", 0)),
        },
        "speed_kmh": float(result.get("speed_kmh", 0.0)),
        "steering": control["steering"],
        "steering_source": "pure_pursuit",
        "centerline": control["centerline"],
        "lane_model": control["lane_model"],
        "lookahead_point": control["lookahead_point"],
    }

    payload.update(
        build_object_payload(
            result,
            homography,
            bev_width,
            bev_height,
            source_width,
            source_height,
            correction,
            include_objects,
            max_objects,
            lane_state,
            object_track_distance,
            object_track_confirm,
            object_track_miss,
            object_track_alpha,
            qt_lanes,
        )
    )

    return payload


# Backward-compatible aliases for older bridge scripts.
_build_lane_payload = build_lane_payload
_build_object_payload = build_object_payload
