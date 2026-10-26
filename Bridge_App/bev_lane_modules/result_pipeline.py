from __future__ import annotations
"""Transform one inference result and publish it to application outputs."""

from dataclasses import dataclass, field
from typing import Any, Dict

from .app_config import PayloadConfig
from .control import IpcSender
from .payload_builder_dual import build_dual_zonal_payload
from .qt_server import QtBroadcastServer
from .scenario import ScenarioManager
from .state import BevLaneState
from .telemetry import DashboardTelemetry


@dataclass
class ResultPipeline:
    """Own the stateful processing steps shared by all board transports.

    Both raw TCP and Vision Protocol deliver the same result dictionary. They
    therefore call this object instead of duplicating payload and output logic.
    """

    qt: QtBroadcastServer
    ipc_sender: IpcSender
    display_config: PayloadConfig
    control_config: PayloadConfig
    scenarios: ScenarioManager
    display_lane_state: BevLaneState = field(default_factory=BevLaneState)
    control_lane_state: BevLaneState = field(default_factory=BevLaneState)
    dashboard_telemetry: DashboardTelemetry = field(default_factory=DashboardTelemetry)

    def process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Build, broadcast, and optionally forward one result payload."""
        payload = build_dual_zonal_payload(
            result,
            self.display_config,
            self.control_config,
            self.display_lane_state,
            self.control_lane_state,
            self.dashboard_telemetry,
            self.scenarios,
        )
        self.qt.broadcast(payload)
        self.ipc_sender.send(
            float(payload["recommended_speed_kmh"]),
            float(payload.get("steering", 0.0)),
            payload["proximity_status"] in ("slowing", "stop"),
            payload["brake_led_simulated"],
        )
        return payload

    def process_safely(self, result: Dict[str, Any]) -> None:
        """Keep transport worker threads alive when a single frame is invalid."""
        try:
            self.process(result)
        except Exception as exc:
            print(f"[zonal-app] payload/result processing error: {exc}")
