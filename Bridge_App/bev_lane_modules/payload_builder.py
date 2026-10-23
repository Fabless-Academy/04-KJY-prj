from __future__ import annotations
"""result JSON을 TOPST_DashBoard가 이해하는 최종 payload로 조립한다."""

from typing import Any, Dict, Optional

from .app_config import PayloadConfig
from .pathing import compute_path_pursuit_steering
from .payload import build_lane_payload
from .payload import build_object_payload
from .payload import compute_lane_model
from .scenario import ScenarioManager
from .state import BevLaneState
from .telemetry import DashboardTelemetry


def build_zonal_payload(
    result: Dict[str, Any],
    config: PayloadConfig,
    lane_state: Optional[BevLaneState],
    dashboard_telemetry: DashboardTelemetry,
    scenarios: ScenarioManager,
) -> Dict[str, Any]:
    """한 프레임 inference result를 Qt/VCP용 최종 payload로 변환한다."""
    qt_lanes = build_lane_payload(
        result,
        config.homography,
        config.bev_width,
        config.bev_height,
        config.source_width,
        config.source_height,
        config.correction,
        config.lane_fit_degree,
        config.lane_fit_samples,
        config.lane_fit_min_points,
        config.lane_top_ratio,
        config.lane_bottom_ratio,
        lane_state,
        config.lane_smoothing,
    )

    # ego 차선(슬롯 1, 2)을 기준으로 주행 경로와 steering을 계산한다.
    steering_deg, raw_path, path, _ = compute_path_pursuit_steering(
        qt_lanes[1],
        qt_lanes[2],
        config.bev_width,
        config.bev_height,
        config.pp_lookahead_ratio,
        config.pp_wheelbase_ratio,
        config.pp_ego_x_ratio,
        config.pp_ego_y_ratio,
        config.pp_max_steer_deg,
        config.path_y_slices,
        config.path_min_y_ratio,
    )
    if lane_state is not None:
        steering_deg = lane_state.smooth_steering(steering_deg, config.steering_smoothing)

    frame_index = int(result.get("frame_index", 0))
    dashboard_values = dashboard_telemetry.update(frame_index)
    scenario_info = scenarios.snapshot()
    payload: Dict[str, Any] = {
        "frame_index": frame_index,
        "width": config.bev_width,
        "height": config.bev_height,
        "lanes": qt_lanes,
        "bev_width": config.bev_width,
        "bev_height": config.bev_height,
        "bev_lanes": qt_lanes,
        "speed_kmh": float(dashboard_values["speed_kmh"]),
        "rpm": float(dashboard_values["rpm"]),
        "fuel_l": float(dashboard_values["fuel_l"]),
        "steering": float(steering_deg),
        "scenario_name": scenario_info["name"],
        "scenario_index": int(scenario_info["index"]),
        "scenario_list": scenario_info["list"],
        "raw_path": raw_path,
        "centerline": path,
        "lane_model": compute_lane_model(qt_lanes[1], qt_lanes[2], config.bev_width, config.bev_height),
    }
    # 객체 payload는 lane payload와 결합되어 lane_id와 lane_status까지 만들어진다.
    payload.update(
        build_object_payload(
            result,
            config.homography,
            config.bev_width,
            config.bev_height,
            config.source_width,
            config.source_height,
            config.correction,
            config.include_objects,
            config.max_objects,
            lane_state,
            config.object_track_distance,
            config.object_track_confirm,
            config.object_track_miss,
            config.object_track_alpha,
            qt_lanes,
        )
    )
    return payload
