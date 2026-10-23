#!/usr/bin/env python3
"""Run the TOPST zonal bridge.

The application has four responsibilities:

1. Receive video and results through raw TCP or Vision Protocol.
2. Convert inference results into display and control BEV coordinates.
3. Publish dashboard JSON and optional MICOM control commands.
4. Manage scenario selection and worker lifecycles.

Detailed math and transport APIs live in bev_lane_modules so this file remains
an executable overview of the complete data flow.
"""

from __future__ import annotations

import argparse
import fcntl
import threading
import time
from contextlib import contextmanager
from typing import Callable, Iterator, List, Optional

from bev_lane_modules.app_config import build_payload_config_for_homography
from bev_lane_modules.cli import parse_args
from bev_lane_modules.control import IpcSender
from bev_lane_modules.qt_server import QtBroadcastServer
from bev_lane_modules.result_pipeline import ResultPipeline
from bev_lane_modules.scenario import ScenarioControlServer, ScenarioManager
from bev_lane_modules.tcp_transport import tcp_result_loop
from bev_lane_modules.video_stream import video_loop
from bev_lane_modules.vision_transport import VisionBridge, vision_result_loop


INSTANCE_LOCK_PATH = "/tmp/zonal_app.lock"


@contextmanager
def single_instance(path: str = INSTANCE_LOCK_PATH) -> Iterator[bool]:
    """Yield whether this process owns the application instance lock."""
    lock_file = open(path, "w", encoding="ascii")
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        lock_file.close()


class ZonalDualBridgeApp:
    """Create services and coordinate the dual-BEV bridge lifecycle."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        display_config = build_payload_config_for_homography(args, args.display_homography)
        control_config = build_payload_config_for_homography(args, args.control_homography)
        print(f"[zonal-app] loaded display homography from {args.display_homography}")
        print(f"[zonal-app] loaded control homography from {args.control_homography}")

        self.stop_event = threading.Event()
        self.qt = QtBroadcastServer(args.qt_host, args.qt_port)
        self.ipc_sender = IpcSender(
            enabled=args.can_enable,
            ipc_path=args.ipc_path,
            period_ms=args.can_period_ms,
        )
        self.scenarios = ScenarioManager(args.scenario_dir, args.video)
        self.control = ScenarioControlServer(args.control_host, args.control_port, self.scenarios)
        self.pipeline = ResultPipeline(
            qt=self.qt,
            ipc_sender=self.ipc_sender,
            display_config=display_config,
            control_config=control_config,
            scenarios=self.scenarios,
        )
        self.vision_bridge: Optional[VisionBridge] = None
        self.threads: List[threading.Thread] = []
        self._started = False

    def start(self) -> None:
        """Start output services, selected board transport, and workers."""
        if self._started:
            return
        self._started = True

        self.qt.start()
        if self.args.can_enable:
            self.ipc_sender.start()
        self.control.start()

        if self.args.transport == "vision":
            self.vision_bridge = VisionBridge(self.args)
            self.vision_bridge.open()
            self.args.vision_bridge = self.vision_bridge

        self._start_result_worker()
        if not self.args.no_video:
            self._start_worker(
                "video-stream",
                video_loop,
                self.args,
                self.scenarios,
                self.stop_event,
            )

    def _start_result_worker(self) -> None:
        if self.args.transport == "vision":
            if self.vision_bridge is None:
                raise RuntimeError("Vision transport selected without initialized bridge")
            self._start_worker(
                "vision-results",
                vision_result_loop,
                self.vision_bridge,
                self.pipeline.process_safely,
                self.stop_event,
            )
            return

        self._start_worker(
            "tcp-results",
            tcp_result_loop,
            self.args.board_host,
            self.args.result_port,
            self.pipeline.process_safely,
            self.stop_event,
        )

    def _start_worker(self, name: str, target: Callable[..., None], *args: object) -> None:
        thread = threading.Thread(name=name, target=target, args=args, daemon=True)
        self.threads.append(thread)
        thread.start()

    def wait(self) -> None:
        """Wait until workers finish or the user presses Ctrl+C."""
        try:
            while any(thread.is_alive() for thread in self.threads):
                time.sleep(0.3)
        except KeyboardInterrupt:
            pass

    def stop(self) -> None:
        """Request shutdown and release every owned resource once."""
        if not self._started:
            return
        self._started = False
        self.stop_event.set()
        self.qt.stop()
        self.control.stop()
        self.ipc_sender.stop()
        if self.vision_bridge is not None:
            self.vision_bridge.close()
            self.vision_bridge = None
        for thread in self.threads:
            thread.join(timeout=1.0)
        self.threads.clear()


def main(argv: Optional[List[str]] = None) -> int:
    """Parse configuration, enforce one instance, and run the application."""
    args = parse_args(argv)
    with single_instance() as acquired:
        if not acquired:
            print("[zonal-app] another instance is already running")
            return 1

        app = ZonalDualBridgeApp(args)
        try:
            app.start()
            app.wait()
        finally:
            app.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
