from __future__ import annotations
"""BEV 변환, 차선 곡선 fitting, 순수 추종 보조 수학 함수를 모아둔다."""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class BevCorrection:
    """호모그래피 이후에 적용하는 후보정 이동/스케일/추가 행렬."""
    post_matrix: Optional[np.ndarray]
    offset_x: float
    offset_y: float
    scale_x: float
    scale_y: float
    pivot_x: float
    pivot_y: float

    def apply_xy(self, x: float, y: float) -> Tuple[int, int]:
        """단일 BEV 점에 후보정 파이프라인을 적용한다."""
        xf = float(x)
        yf = float(y)
        if self.post_matrix is not None:
            m = self.post_matrix.astype(np.float64)
            v = np.array([xf, yf, 1.0], dtype=np.float64)
            w = m @ v
            if abs(w[2]) < 1e-12:
                return int(round(xf)), int(round(yf))
            xf = w[0] / w[2]
            yf = w[1] / w[2]
        xf = (xf - self.pivot_x) * self.scale_x + self.pivot_x + self.offset_x
        yf = (yf - self.pivot_y) * self.scale_y + self.pivot_y + self.offset_y
        return int(round(xf)), int(round(yf))


def load_matrix3_json(path: str) -> np.ndarray:
    """JSON 파일에서 3x3 호모그래피 또는 보정 행렬을 읽는다."""
    with open(path, "r", encoding="utf-8") as file:
        raw = json.load(file)
    matrix = raw.get("matrix", raw.get("homography", raw))
    arr = np.asarray(matrix, dtype=np.float32)
    if arr.shape != (3, 3):
        raise ValueError(f"expected 3x3 matrix, got {arr.shape}")
    return arr


def merge_bev_correction(
    bev_w: int,
    bev_h: int,
    tweak_json_path: Optional[str],
    post_matrix_path: Optional[str],
    offset_x: Optional[float],
    offset_y: Optional[float],
    scale_x: Optional[float],
    scale_y: Optional[float],
    pivot_x: Optional[float],
    pivot_y: Optional[float],
) -> BevCorrection:
    """파일/CLI에서 받은 BEV 후보정 값을 하나의 객체로 합친다."""
    values: Dict[str, float] = {
        "offset_x": 0.0,
        "offset_y": 0.0,
        "scale_x": 1.0,
        "scale_y": 1.0,
        "pivot_x": bev_w / 2.0,
        "pivot_y": bev_h / 2.0,
    }
    if tweak_json_path:
        with open(tweak_json_path, "r", encoding="utf-8") as file:
            tweak = json.load(file)
        for key in values:
            if key in tweak:
                values[key] = float(tweak[key])
    if offset_x is not None:
        values["offset_x"] = offset_x
    if offset_y is not None:
        values["offset_y"] = offset_y
    if scale_x is not None:
        values["scale_x"] = scale_x
    if scale_y is not None:
        values["scale_y"] = scale_y
    if pivot_x is not None:
        values["pivot_x"] = pivot_x
    if pivot_y is not None:
        values["pivot_y"] = pivot_y

    post_matrix = load_matrix3_json(post_matrix_path) if post_matrix_path else None
    return BevCorrection(
        post_matrix,
        values["offset_x"],
        values["offset_y"],
        values["scale_x"],
        values["scale_y"],
        values["pivot_x"],
        values["pivot_y"],
    )


def correction_json_has_values(path: Optional[str]) -> bool:
    """주어진 JSON에 BEV 후보정 키가 실제로 들어 있는지 확인한다."""
    if not path:
        return False
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        return False
    return any(
        key in payload
        for key in ("offset_x", "offset_y", "scale_x", "scale_y", "pivot_x", "pivot_y")
    )


def fit_lane_curve(
    points: List[Dict[str, Any]],
    degree: int,
    sample_count: int,
    min_points: int,
    top_y: Optional[float] = None,
    bottom_y: Optional[float] = None,
) -> List[Dict[str, int]]:
    """차선 점 집합을 y축 기준 다항식으로 근사해 균일 샘플로 다시 만든다."""
    if len(points) < max(2, min_points):
        return [{"x": int(round(float(p.get("x", 0)))), "y": int(round(float(p.get("y", 0))))} for p in points]

    sorted_points = sorted(points, key=lambda p: float(p.get("y", 0.0)), reverse=True)
    ys = np.array([float(point.get("y", 0.0)) for point in sorted_points], dtype=np.float32)
    xs = np.array([float(point.get("x", 0.0)) for point in sorted_points], dtype=np.float32)

    unique_ys, unique_indices = np.unique(ys, return_index=True)
    xs = xs[unique_indices]
    ys = unique_ys
    if len(ys) < max(2, min_points):
        return [{"x": int(round(float(p.get("x", 0)))), "y": int(round(float(p.get("y", 0))))} for p in sorted_points]

    fit_degree = min(max(1, degree), len(ys) - 1)
    if fit_degree < 1:
        return [{"x": int(round(float(p.get("x", 0)))), "y": int(round(float(p.get("y", 0))))} for p in sorted_points]

    try:
        coeffs = np.polyfit(ys, xs, fit_degree)
    except (np.linalg.LinAlgError, ValueError):
        return [{"x": int(round(float(p.get("x", 0)))), "y": int(round(float(p.get("y", 0))))} for p in sorted_points]

    observed_bottom_y = float(np.max(ys))
    observed_top_y = float(np.min(ys))
    y_start = observed_bottom_y if bottom_y is None else min(float(bottom_y), observed_bottom_y)
    y_end = observed_top_y if top_y is None else max(float(top_y), observed_top_y)
    if abs(y_start - y_end) < 1e-3:
        return [{"x": int(round(float(p.get("x", 0)))), "y": int(round(float(p.get("y", 0))))} for p in sorted_points]

    sample_ys = np.linspace(y_start, y_end, max(2, sample_count), dtype=np.float32)
    sample_xs = np.polyval(coeffs, sample_ys)
    return [{"x": int(round(float(x_val))), "y": int(round(float(y_val)))} for x_val, y_val in zip(sample_xs, sample_ys)]


def fit_lane_set(
    lane_set: List[List[Dict[str, Any]]],
    degree: int,
    sample_count: int,
    min_points: int,
    top_y: Optional[float] = None,
    bottom_y: Optional[float] = None,
) -> List[List[Dict[str, int]]]:
    """최대 4개 차선 슬롯 각각에 fitting을 적용한다."""
    fitted_set: List[List[Dict[str, int]]] = [[], [], [], []]
    for lane_idx in range(4):
        lane_points = lane_set[lane_idx] if lane_idx < len(lane_set) else []
        fitted_set[lane_idx] = fit_lane_curve(lane_points, degree, sample_count, min_points, top_y, bottom_y)
    return fitted_set


def scale_points(
    points: List[Dict[str, Any]],
    src_w: int,
    src_h: int,
    dst_w: int,
    dst_h: int,
) -> List[Dict[str, float]]:
    """원본 해상도 좌표를 목적 해상도 비율로 선형 스케일한다."""
    sx = float(dst_w) / max(src_w, 1)
    sy = float(dst_h) / max(src_h, 1)
    return [{"x": float(p.get("x", 0.0)) * sx, "y": float(p.get("y", 0.0)) * sy} for p in points]


def transform_points(
    points: List[Dict[str, Any]],
    homography: np.ndarray,
    src_w: int,
    src_h: int,
    dst_w: int,
    dst_h: int,
    correction: Optional[BevCorrection] = None,
) -> List[Dict[str, int]]:
    """원본 점들을 목적 해상도로 스케일한 뒤 호모그래피와 후보정을 적용한다."""
    scaled = scale_points(points, src_w, src_h, dst_w, dst_h)
    if not scaled:
        return []
    src = np.array([[[p["x"], p["y"]] for p in scaled]], dtype=np.float32)
    dst = cv2.perspectiveTransform(src, homography)[0]
    output: List[Dict[str, int]] = []
    for x, y in dst:
        ix, iy = correction.apply_xy(float(x), float(y)) if correction is not None else (int(round(x)), int(round(y)))
        output.append({"x": ix, "y": iy})
    return output


def transform_object_foot(
    obj: Dict[str, Any],
    homography: np.ndarray,
    src_w: int,
    src_h: int,
    dst_w: int,
    dst_h: int,
    correction: Optional[BevCorrection] = None,
) -> Dict[str, Any]:
    """객체 bbox 하단 중심점을 BEV 좌표로 변환해 원본 객체 dict에 추가한다."""
    output = dict(obj)
    x_min = float(obj.get("x_min", 0.0))
    x_max = float(obj.get("x_max", 0.0))
    y_max = float(obj.get("y_max", 0.0))
    foot = [{"x": 0.5 * (x_min + x_max), "y": y_max}]
    point = transform_points(foot, homography, src_w, src_h, dst_w, dst_h, correction)[0]
    output["bev_x"] = point["x"]
    output["bev_y"] = point["y"]
    return output


def build_centerline(
    left_lane: List[Dict[str, int]],
    right_lane: List[Dict[str, int]],
) -> List[Dict[str, int]]:
    """좌우 ego 차선으로부터 단순 centerline을 만든다."""
    if not left_lane or not right_lane:
        return []
    point_count = min(len(left_lane), len(right_lane))
    return [
        {
            "x": int(round((float(left_lane[i]["x"]) + float(right_lane[i]["x"])) * 0.5)),
            "y": int(round((float(left_lane[i]["y"]) + float(right_lane[i]["y"])) * 0.5)),
        }
        for i in range(point_count)
    ]


def choose_lookahead_point(centerline: List[Dict[str, int]], target_y: float) -> Optional[Dict[str, int]]:
    if not centerline:
        return None
    return min(centerline, key=lambda point: abs(float(point["y"]) - target_y))


def compute_pure_pursuit_steering(
    left_lane: List[Dict[str, int]],
    right_lane: List[Dict[str, int]],
    bev_width: int,
    bev_height: int,
    lookahead_ratio: float,
    wheelbase_ratio: float,
    ego_x_ratio: float,
    ego_y_ratio: float,
    max_steer_deg: float,
) -> Tuple[float, List[Dict[str, int]], Optional[Dict[str, int]]]:
    centerline = build_centerline(left_lane, right_lane)
    if not centerline:
        return 0.0, [], None

    ego_x = float(bev_width) * ego_x_ratio
    ego_y = float(bev_height) * ego_y_ratio
    target_y = float(bev_height) * lookahead_ratio
    lookahead_point = choose_lookahead_point(centerline, target_y)
    if lookahead_point is None:
        return 0.0, centerline, None

    dx = float(lookahead_point["x"]) - ego_x
    dy = ego_y - float(lookahead_point["y"])
    if dy <= 1e-3:
        return 0.0, centerline, lookahead_point

    lookahead_dist = max((dx * dx + dy * dy) ** 0.5, 1e-3)
    wheelbase = max(float(bev_height) * wheelbase_ratio, 1e-3)
    alpha = float(np.arctan2(dx, dy))
    steering_rad = float(np.arctan2(2.0 * wheelbase * np.sin(alpha), lookahead_dist))
    steering_deg = float(np.degrees(steering_rad))
    steering_deg = max(-max_steer_deg, min(max_steer_deg, steering_deg))
    return steering_deg, centerline, lookahead_point
