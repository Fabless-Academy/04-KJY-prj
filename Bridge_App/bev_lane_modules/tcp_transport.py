from __future__ import annotations
"""Legacy raw-TCP result transport used by zonal_app."""

import json
import threading
import time
from typing import Any, Callable, Dict

from .net import connect_with_retry


ResultHandler = Callable[[Dict[str, Any]], None]


def dispatch_complete_lines(buffer: bytes, process_result: ResultHandler) -> bytes:
    """Decode all newline-delimited JSON messages and return the remainder."""
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        line = line.strip()
        if not line:
            continue
        try:
            result = json.loads(line.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        if isinstance(result, dict):
            process_result(result)
    return buffer


def tcp_result_loop(
    board_host: str,
    result_port: int,
    process_result: ResultHandler,
    stop_event: threading.Event,
) -> None:
    """Receive newline-delimited inference JSON and reconnect on disconnect."""
    while not stop_event.is_set():
        try:
            sock = connect_with_retry(board_host, result_port, stop_event, "JSON")
        except RuntimeError:
            return

        buffer = b""
        print(f"[zonal-app] JSON connected {board_host}:{result_port}")
        try:
            while not stop_event.is_set():
                data = sock.recv(4096)
                if not data:
                    print("[zonal-app] JSON disconnected, retry")
                    break
                buffer = dispatch_complete_lines(buffer + data, process_result)
        except OSError as exc:
            print(f"[zonal-app] result error: {exc}")
        finally:
            try:
                sock.close()
            except OSError:
                pass

        if not stop_event.is_set():
            time.sleep(0.5)
