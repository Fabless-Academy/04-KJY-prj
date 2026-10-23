from __future__ import annotations
"""브리지 전역 고정 설정과 payload 설정 객체를 정의한다."""

import argparse
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

from .geometry import BevCorrection
from .geometry import correction_json_has_values
from .geometry import load_matrix3_json
from .geometry import merge_bev_correction


FIXED_DEFAULTS: Dict[str, Any] = {
    "width": 1280,
    "height": 720,
    "pixel_order": "bgr",
    "bev_width": 1280,
    "bev_height": 720,
    "max_objects": 32,
    "object_track_distance": 60.0,
    "object_track_confirm": 2,
    "object_track_miss": 4,
    "object_track_alpha": 0.7,
    "fps": None,
    "no_throttle": False,
    "no_video": False,
    "bev_tweak_json": None,
    "bev_post_matrix": None,
    "bev_offset_x": None,
    "bev_offset_y": None,
    "bev_scale_x": None,
    "bev_scale_y": None,
    "bev_pivot_x": None,
    "bev_pivot_y": None,
    "lane_fit_degree": 2,
    "lane_fit_samples": 24,
    "lane_fit_min_points": 4,
    "lane_smoothing": 0.88,
    "steering_smoothing": 0.88,
    "lane_top_ratio": 0.12,
    "lane_bottom_ratio": 0.97,
    "pp_lookahead_ratio": 0.58,
    "pp_wheelbase_ratio": 0.12,
    "pp_ego_x_ratio": 0.5,
    "pp_ego_y_ratio": 0.97,
    "pp_max_steer_deg": 35.0,
    "path_y_slices": 20,
    "path_min_y_ratio": 0.35,
}


@dataclass(frozen=True)
class PayloadConfig:
    """한 프레임 payload를 만들 때 필요한 튜닝값/크기 정보를 묶은 설정 객체."""
    homography: np.ndarray
    bev_width: int
    bev_height: int
    source_width: int
    source_height: int
    include_objects: bool
    max_objects: int
    correction: Optional[BevCorrection]
    lane_fit_degree: int
    lane_fit_samples: int
    lane_fit_min_points: int
    lane_top_ratio: float
    lane_bottom_ratio: float
    lane_smoothing: float
    steering_smoothing: float
    pp_lookahead_ratio: float
    pp_wheelbase_ratio: float
    pp_ego_x_ratio: float
    pp_ego_y_ratio: float
    pp_max_steer_deg: float
    path_y_slices: int
    path_min_y_ratio: float
    object_track_distance: float
    object_track_confirm: int
    object_track_miss: int
    object_track_alpha: float
    obstacle_slowdown_y_ratio: float
    obstacle_stop_y_ratio: float


def apply_fixed_defaults(args: argparse.Namespace) -> argparse.Namespace:
    """CLI에 노출하지 않는 내부 기본값을 argparse 결과에 주입한다."""
    for key, value in FIXED_DEFAULTS.items():
        setattr(args, key, value)
    return args


def load_bev_correction(
    args: argparse.Namespace,
    homography_path: Optional[str] = None,
) -> Optional[BevCorrection]:
    """BEV 후보정 파라미터를 homography/CLI 설정에서 합쳐 읽어온다."""
    tweak_source = args.bev_tweak_json
    correction_source = homography_path or args.homography
    if tweak_source is None and correction_json_has_values(correction_source):
        tweak_source = correction_source

    return merge_bev_correction(
        args.bev_width,
        args.bev_height,
        tweak_source,
        args.bev_post_matrix,
        args.bev_offset_x,
        args.bev_offset_y,
        args.bev_scale_x,
        args.bev_scale_y,
        args.bev_pivot_x,
        args.bev_pivot_y,
    )


def build_payload_config(
    args: argparse.Namespace,
    homography: np.ndarray,
    correction: Optional[BevCorrection],
) -> PayloadConfig:
    """argparse 결과와 보정 행렬을 최종 PayloadConfig로 변환한다."""
    return PayloadConfig(
        homography=homography,
        bev_width=args.bev_width,
        bev_height=args.bev_height,
        source_width=args.width,
        source_height=args.height,
        include_objects=not args.no_objects,
        max_objects=args.max_objects,
        correction=correction,
        lane_fit_degree=args.lane_fit_degree,
        lane_fit_samples=args.lane_fit_samples,
        lane_fit_min_points=args.lane_fit_min_points,
        lane_top_ratio=args.lane_top_ratio,
        lane_bottom_ratio=args.lane_bottom_ratio,
        lane_smoothing=args.lane_smoothing,
        steering_smoothing=args.steering_smoothing,
        pp_lookahead_ratio=args.pp_lookahead_ratio,
        pp_wheelbase_ratio=args.pp_wheelbase_ratio,
        pp_ego_x_ratio=args.pp_ego_x_ratio,
        pp_ego_y_ratio=args.pp_ego_y_ratio,
        pp_max_steer_deg=args.pp_max_steer_deg,
        path_y_slices=args.path_y_slices,
        path_min_y_ratio=args.path_min_y_ratio,
        object_track_distance=args.object_track_distance,
        object_track_confirm=args.object_track_confirm,
        object_track_miss=args.object_track_miss,
        object_track_alpha=args.object_track_alpha,
        obstacle_slowdown_y_ratio=args.obstacle_slowdown_y_ratio,
        obstacle_stop_y_ratio=args.obstacle_stop_y_ratio,
    )

def build_payload_config_for_homography(
    args: argparse.Namespace,
    homography_path: str,
) -> PayloadConfig:
    """Build a payload config without mutating the shared argument namespace."""
    homography = load_matrix3_json(homography_path)
    correction = load_bev_correction(args, homography_path)
    return build_payload_config(args, homography, correction)
