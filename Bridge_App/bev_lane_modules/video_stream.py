from __future__ import annotations
"""선택된 시나리오 영상을 topst-nn-server 입력으로 계속 송신한다."""

import argparse
import os
import threading
import time

import cv2

from .net import connect_with_retry
from .scenario import ScenarioManager


def open_video(path: str):
    """영상 파일을 열고 실패 시 명확한 예외를 발생시킨다."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {path}")
    return cap


def _frame_bytes(args: argparse.Namespace, frame) -> bytes:
    small = cv2.resize(frame, (args.width, args.height), interpolation=cv2.INTER_AREA)
    if args.pixel_order == "rgb":
        return cv2.cvtColor(small, cv2.COLOR_BGR2RGB).tobytes()
    return small.tobytes()


def _sleep_for_interval(interval: float, started_at: float) -> None:
    sleep = interval - (time.time() - started_at)
    if interval > 0.0 and sleep > 0.0:
        time.sleep(sleep)


def video_loop(args: argparse.Namespace, scenarios: ScenarioManager, stop_event: threading.Event) -> None:
    """현재 선택된 시나리오 영상을 반복 재생하며 RGB 프레임을 보드로 전송한다."""
    current_generation = -1
    cap = None
    interval = 0.0

    def open_current_video(path: str):
        local_cap = open_video(path)
        local_fps = args.fps if args.fps is not None else local_cap.get(cv2.CAP_PROP_FPS)
        if local_fps <= 0.0:
            local_fps = 30.0
        local_interval = 0.0 if args.no_throttle else 1.0 / local_fps
        print(f"[zonal-test] using scenario video {path}")
        return local_cap, local_interval

    try:
        while not stop_event.is_set():
            scenario_info = scenarios.snapshot()
            if cap is None or scenario_info["generation"] != current_generation:
                if cap is not None:
                    cap.release()
                current_generation = scenario_info["generation"]
                cap, interval = open_current_video(os.path.abspath(scenario_info["path"]))

            if getattr(args, "transport", "tcp") == "vision":
                bridge = getattr(args, "vision_bridge", None)
                if bridge is None:
                    raise RuntimeError("Vision transport selected without a VisionBridge")
                print(
                    f"[zonal-test] video -> vision stream:{args.stream_port} "
                    f"{args.width}x{args.height} {args.pixel_order.upper()}"
                )
                while not stop_event.is_set():
                    scenario_info = scenarios.snapshot()
                    if scenario_info["generation"] != current_generation:
                        break
                    t0 = time.time()
                    ok, frame = cap.read()
                    if not ok:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    if not bridge.send_frame(_frame_bytes(args, frame)):
                        time.sleep(0.001)
                    _sleep_for_interval(interval, t0)
                continue

            sock = connect_with_retry(args.board_host, args.video_port, stop_event, "video")
            print(
                f"[zonal-test] video -> {args.board_host}:{args.video_port} "
                f"{args.width}x{args.height} {args.pixel_order.upper()}"
            )
            try:
                while not stop_event.is_set():
                    scenario_info = scenarios.snapshot()
                    if scenario_info["generation"] != current_generation:
                        break

                    t0 = time.time()
                    ok, frame = cap.read()
                    if not ok:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue

                    sock.sendall(_frame_bytes(args, frame))
                    _sleep_for_interval(interval, t0)
            except OSError as exc:
                print(f"[zonal-test] video error: {exc}")
                time.sleep(0.5)
            finally:
                try:
                    sock.close()
                except OSError:
                    pass
    finally:
        if cap is not None:
            cap.release()
