from __future__ import annotations
"""Command-line interface for the zonal bridge application."""

import argparse
from typing import Optional, Sequence

from .app_config import apply_fixed_defaults
from .control import IPC_PATH
from .scenario import DEFAULT_CONTROL_PORT, DEFAULT_SCENARIO_DIR


DEFAULT_BOARD_HOST = "192.168.0.100"
DEFAULT_STREAM_PORT = 9998
DEFAULT_MESSAGE_PORT = 9999


def build_parser() -> argparse.ArgumentParser:
    """Build the parser without reading process arguments.

    Keeping parser construction separate makes the CLI easy to document and
    test without starting sockets or loading the Vision Protocol library.
    """
    parser = argparse.ArgumentParser(description="Zonal dual-BEV lane bridge")

    transport = parser.add_argument_group("board transport")
    transport.add_argument(
        "--transport",
        choices=("tcp", "vision"),
        default="vision",
        help="Board transport (default: vision)",
    )
    transport.add_argument(
        "--board-host",
        default=DEFAULT_BOARD_HOST,
        help="Inference host for raw TCP mode",
    )
    transport.add_argument("--video-port", type=int, default=9999, help="RGB TCP port")
    transport.add_argument("--result-port", type=int, default=9998, help="JSON result TCP port")
    transport.add_argument(
        "--stream-port",
        type=int,
        default=DEFAULT_STREAM_PORT,
        help="Vision Protocol stream port",
    )
    transport.add_argument(
        "--message-port",
        type=int,
        default=DEFAULT_MESSAGE_PORT,
        help="Vision Protocol message port",
    )
    transport.add_argument(
        "--rtpm-root",
        default="/mnt/c/ai_work/rtpm",
        help="Fallback directory containing the Vision Protocol library",
    )

    dashboard = parser.add_argument_group("dashboard and scenarios")
    dashboard.add_argument("--qt-host", default="0.0.0.0", help="Bind address for Qt clients")
    dashboard.add_argument("--qt-port", type=int, default=10000, help="Port for Qt clients")
    dashboard.add_argument(
        "--control-host",
        default="0.0.0.0",
        help="Bind address for scenario control clients",
    )
    dashboard.add_argument(
        "--control-port",
        type=int,
        default=DEFAULT_CONTROL_PORT,
        help="Port for scenario control clients",
    )
    dashboard.add_argument(
        "--scenario-dir",
        default=DEFAULT_SCENARIO_DIR,
        help="Directory containing scenario video files",
    )
    dashboard.add_argument("--video", default="output.mp4", help="Fallback video file")

    bev = parser.add_argument_group("BEV processing")
    bev.add_argument(
        "--display-homography",
        default="display_bev.json",
        help="Homography JSON used for dashboard rendering",
    )
    bev.add_argument(
        "--control-homography",
        default="control_bev.json",
        help="Homography JSON used for steering and curvature",
    )
    bev.add_argument(
        "--no-objects",
        action="store_true",
        help="Do not transform or forward detected objects",
    )
    bev.add_argument(
        "--obstacle-slowdown-y-ratio",
        type=float,
        default=0.30,
        help="BEV y/height ratio where distance-based target speed reduction starts (default: 0.30)",
    )
    bev.add_argument(
        "--obstacle-stop-y-ratio",
        type=float,
        default=0.70,
        help="BEV y/height ratio where distance-based target speed reaches zero (default: 0.70)",
    )

    vehicle = parser.add_argument_group("vehicle control")
    vehicle.add_argument("--can-enable", action="store_true", help="Enable MICOM IPC output")
    vehicle.add_argument("--ipc-path", default=IPC_PATH, help="MICOM IPC device path")
    vehicle.add_argument(
        "--can-period-ms",
        type=int,
        default=50,
        help="Minimum period between IPC sends",
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments and add the internal processing defaults."""
    args = apply_fixed_defaults(build_parser().parse_args(argv))
    if not 0.0 <= args.obstacle_slowdown_y_ratio < args.obstacle_stop_y_ratio <= 1.0:
        raise ValueError(
            "obstacle y ratios must satisfy "
            "0 <= --obstacle-slowdown-y-ratio < --obstacle-stop-y-ratio <= 1"
        )

    # Kept for compatibility with helpers that expect a primary homography.
    args.homography = args.display_homography
    print(
        f"[zonal-app] transport={args.transport} "
        f"stream={args.stream_port} message={args.message_port}"
    )
    return args
