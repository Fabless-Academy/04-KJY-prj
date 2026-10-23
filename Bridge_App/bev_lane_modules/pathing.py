from __future__ import annotations
"""BEV ego 차선으로부터 경로와 pure-pursuit steering을 계산한다."""

from typing import Dict, List, Optional, Tuple

import numpy as np


Point = Dict[str, int]


def _as_sorted_array(points: List[Point]) -> np.ndarray:
    """점 목록을 y축 기준 정렬된 numpy 배열로 변환한다."""
    if not points:
        return np.empty((0, 2), dtype=np.float64)
    arr = np.array(
        [[float(point.get("x", 0.0)), float(point.get("y", 0.0))] for point in points],
        dtype=np.float64,
    )
    return arr[np.argsort(arr[:, 1])]


def _interp_lane_x(points: List[Point], target_y: float) -> Optional[float]:
    """주어진 y 위치에서 차선의 x 좌표를 선형 보간한다."""
    arr = _as_sorted_array(points)
    if len(arr) < 2:
        return None

    ys = arr[:, 1]
    xs = arr[:, 0]
    if target_y <= ys.min() or target_y >= ys.max():
        return None

    for idx in range(len(arr) - 1):
        y0, y1 = ys[idx], ys[idx + 1]
        if abs(y1 - y0) < 1e-6:
            continue
        low = min(y0, y1)
        high = max(y0, y1)
        if low <= target_y <= high:
            t = (target_y - y0) / (y1 - y0)
            return float((1.0 - t) * xs[idx] + t * xs[idx + 1])
    return None


def build_path_from_lanes(
    left_lane: List[Point],
    right_lane: List[Point],
    bev_height: int,
    path_y_slices: int,
    bev_y_min: float,
) -> Tuple[List[Point], List[Point]]:
    """좌우 ego 차선 경계로부터 raw path와 fitted path를 만든다."""
    if len(left_lane) < 2 or len(right_lane) < 2:
        return [], []

    y_step = max(5, int(round(float(bev_height) / max(path_y_slices, 1))))
    raw_points: List[Tuple[float, float]] = []
    for bin_idx in range((bev_height + y_step - 1) // y_step):
        y = (bin_idx + 0.5) * y_step
        if y >= bev_height or y < bev_y_min:
            continue
        # 같은 y 위치에서 좌/우 차선의 중점을 path 점으로 사용한다.
        x_left = _interp_lane_x(left_lane, y)
        x_right = _interp_lane_x(right_lane, y)
        if x_left is None or x_right is None:
            continue
        raw_points.append(((x_left + x_right) * 0.5, y))

    raw_points.sort(key=lambda point: point[1])
    raw_path = [{"x": int(round(x)), "y": int(round(y))} for x, y in raw_points]
    if len(raw_points) < 3:
        return raw_path, raw_path

    path_array = np.array(raw_points, dtype=np.float64)
    ys_raw = path_array[:, 1]
    xs_raw = path_array[:, 0]
    degree = min(3, len(ys_raw) - 1)
    if degree < 1:
        return raw_path, raw_path

    try:
        coeffs = np.polyfit(ys_raw, xs_raw, deg=degree)
    except (np.linalg.LinAlgError, ValueError):
        return raw_path, raw_path

    y_min = float(ys_raw[0])
    y_max = float(ys_raw[-1])
    sample_ys = np.linspace(y_min, y_max, path_y_slices, dtype=np.float64)
    sample_xs = np.polyval(coeffs, sample_ys)
    fitted_path = [
        {"x": int(round(float(x_val))), "y": int(round(float(y_val)))}
        for x_val, y_val in zip(sample_xs, sample_ys)
    ]
    return raw_path, fitted_path


def interpolate_path_point(path_points: List[Point], target_y: float) -> Optional[Dict[str, float]]:
    """경로 위에서 target_y에 해당하는 점을 보간해 찾는다."""
    arr = _as_sorted_array(path_points)
    if len(arr) < 2:
        return None

    ys = arr[:, 1]
    xs = arr[:, 0]
    if target_y <= ys.min():
        return {"x": float(xs[0]), "y": float(ys[0])}
    if target_y >= ys.max():
        return {"x": float(xs[-1]), "y": float(ys[-1])}

    for idx in range(len(arr) - 1):
        y0, y1 = ys[idx], ys[idx + 1]
        if abs(y1 - y0) < 1e-6:
            continue
        low = min(y0, y1)
        high = max(y0, y1)
        if low <= target_y <= high:
            t = (target_y - y0) / (y1 - y0)
            x = (1.0 - t) * xs[idx] + t * xs[idx + 1]
            return {"x": float(x), "y": float(target_y)}
    return None


def compute_path_pursuit_steering(
    left_lane: List[Point],
    right_lane: List[Point],
    bev_width: int,
    bev_height: int,
    lookahead_ratio: float,
    wheelbase_ratio: float,
    ego_x_ratio: float,
    ego_y_ratio: float,
    max_steer_deg: float,
    path_y_slices: int,
    path_min_y_ratio: float,
) -> Tuple[float, List[Point], List[Point], Optional[Point]]:
    """Pure pursuit 방식으로 steering, raw path, fitted path, lookahead를 계산한다."""
    raw_path, path = build_path_from_lanes(
        left_lane,
        right_lane,
        bev_height,
        path_y_slices=path_y_slices,
        bev_y_min=float(bev_height) * path_min_y_ratio,
    )
    if len(path) < 2:
        return 0.0, raw_path, path, None

    ego_x = float(bev_width) * ego_x_ratio
    ego_y = float(bev_height) * ego_y_ratio
    target_y = float(bev_height) * lookahead_ratio
    lookahead = interpolate_path_point(path, target_y)
    if lookahead is None:
        return 0.0, raw_path, path, None

    dx = float(lookahead["x"]) - ego_x
    dy = ego_y - float(lookahead["y"])
    if dy <= 1e-3:
        return 0.0, raw_path, path, {"x": int(round(lookahead["x"])), "y": int(round(lookahead["y"]))}

    lookahead_dist = max((dx * dx + dy * dy) ** 0.5, 1e-3)
    wheelbase = max(float(bev_height) * wheelbase_ratio, 1e-3)
    alpha = float(np.arctan2(dx, dy))
    steering_rad = float(np.arctan2(2.0 * wheelbase * np.sin(alpha), lookahead_dist))
    steering_deg = float(np.degrees(steering_rad))
    steering_deg = max(-max_steer_deg, min(max_steer_deg, steering_deg))
    return steering_deg, raw_path, path, {"x": int(round(lookahead["x"])), "y": int(round(lookahead["y"]))}
