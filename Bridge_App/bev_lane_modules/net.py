from __future__ import annotations
"""단순 TCP 연결과 재시도 로직을 공통화한 모듈."""

import socket
import threading
import time


def connect(host: str, port: int) -> socket.socket:
    """호스트와 포트로 TCP 연결을 생성한다."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    return sock


def connect_with_retry(host: str, port: int, stop_event: threading.Event, label: str) -> socket.socket:
    """stop_event가 해제될 때까지 연결을 반복 시도한다."""
    while not stop_event.is_set():
        try:
            return connect(host, port)
        except OSError as exc:
            print(f"[zonal-test] waiting for {label} {host}:{port} ({exc})")
            time.sleep(1.0)
    raise RuntimeError(f"stopped while waiting for {label}")
