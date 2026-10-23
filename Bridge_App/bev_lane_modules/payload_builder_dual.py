from __future__ import annotations
"""표시용 BEV와 제어용 BEV를 분리해 최종 payload를 조립한다."""

from typing import Any, Dict, Optional

from .app_config import PayloadConfig
from .pathing import compute_path_pursuit_steering
from .payload import build_lane_payload
from .payload import build_object_payload
from .payload import compute_lane_model
from .proximity import calculate_bev_speed_recommendation
from .scenario import ScenarioManager
from .state import BevLaneState
from .telemetry import DashboardTelemetry


def build_dual_zonal_payload(
    result: Dict[str, Any],
    display_config: PayloadConfig,
    control_config: PayloadConfig,
    display_lane_state: Optional[BevLaneState],
    control_lane_state: Optional[BevLaneState],
    dashboard_telemetry: DashboardTelemetry,
    scenarios: ScenarioManager,
) -> Dict[str, Any]:
    """표시용 BEV와 제어용 BEV를 따로 사용해 Qt/VCP용 payload를 만든다."""
    display_lanes = build_lane_payload(
        result,
        display_config.homography,
        display_config.bev_width,
        display_config.bev_height,
        display_config.source_width,
        display_config.source_height,
        display_config.correction,
        display_config.lane_fit_degree,
        display_config.lane_fit_samples,
        display_config.lane_fit_min_points,
        display_config.lane_top_ratio,
        display_config.lane_bottom_ratio,
        display_lane_state,
        display_config.lane_smoothing,
    )

    control_lanes = build_lane_payload(
        result,
        control_config.homography,
        control_config.bev_width,
        control_config.bev_height,
        control_config.source_width,
        control_config.source_height,
        control_config.correction,
        control_config.lane_fit_degree,
        control_config.lane_fit_samples,
        control_config.lane_fit_min_points,
        control_config.lane_top_ratio,
        control_config.lane_bottom_ratio,
        control_lane_state,
        control_config.lane_smoothing,
    )

    # 화면에 그릴 path는 표시용 차선 좌표계에서 계산해 lane과 시각적으로 맞춘다.
    _, display_raw_path, display_path, _ = compute_path_pursuit_steering(
        display_lanes[1],
        display_lanes[2],
        display_config.bev_width,
        display_config.bev_height,
        display_config.pp_lookahead_ratio,
        display_config.pp_wheelbase_ratio,
        display_config.pp_ego_x_ratio,
        display_config.pp_ego_y_ratio,
        display_config.pp_max_steer_deg,
        display_config.path_y_slices,
        display_config.path_min_y_ratio,
    )

    # 실제 steering/lane_model은 평평하게 펴진 제어용 좌표계에서 계산한다.
    steering_deg, _, _, _ = compute_path_pursuit_steering(
        control_lanes[1],
        control_lanes[2],
        control_config.bev_width,
        control_config.bev_height,
        control_config.pp_lookahead_ratio,
        control_config.pp_wheelbase_ratio,
        control_config.pp_ego_x_ratio,
        control_config.pp_ego_y_ratio,
        control_config.pp_max_steer_deg,
        control_config.path_y_slices,
        control_config.path_min_y_ratio,
    )
    if control_lane_state is not None:
        steering_deg = control_lane_state.smooth_steering(steering_deg, control_config.steering_smoothing)

    frame_index = int(result.get("frame_index", 0))
    dashboard_values = dashboard_telemetry.update(frame_index)
    scenario_info = scenarios.snapshot()
    payload: Dict[str, Any] = {
        "frame_index": frame_index,
        "width": display_config.bev_width,
        "height": display_config.bev_height,
        "lanes": display_lanes,
        "bev_width": display_config.bev_width,
        "bev_height": display_config.bev_height,
        "bev_lanes": display_lanes,
        "speed_kmh": float(dashboard_values["speed_kmh"]),
        "rpm": float(dashboard_values["rpm"]),
        "fuel_l": float(dashboard_values["fuel_l"]),
        "steering": float(steering_deg),
        "scenario_name": scenario_info["name"],
        "scenario_index": int(scenario_info["index"]),
        "scenario_list": scenario_info["list"],
        "raw_path": display_raw_path,
        "centerline": display_path,
        "lane_model": compute_lane_model(
            control_lanes[1],
            control_lanes[2],
            control_config.bev_width,
            control_config.bev_height,
        ),
    }
    payload.update(
        build_object_payload(
            result,
            display_config.homography,
            display_config.bev_width,
            display_config.bev_height,
            display_config.source_width,
            display_config.source_height,
            display_config.correction,
            display_config.include_objects,
            display_config.max_objects,
            display_lane_state,
            display_config.object_track_distance,
            display_config.object_track_confirm,
            display_config.object_track_miss,
            display_config.object_track_alpha,
            display_lanes,
        )
    )
    payload.update(
        calculate_bev_speed_recommendation(
            payload["bev_objects"],
            display_config.bev_height,
            display_config.obstacle_slowdown_y_ratio,
            display_config.obstacle_stop_y_ratio,
        )
    )
    payload["speed_control_mode"] = "distance"
    payload["brake_led_simulated"] = payload["proximity_status"] in ("slowing", "stop")
    payload["obstacle_slowdown_y_ratio"] = display_config.obstacle_slowdown_y_ratio
    payload["obstacle_stop_y_ratio"] = display_config.obstacle_stop_y_ratio
    return payload
