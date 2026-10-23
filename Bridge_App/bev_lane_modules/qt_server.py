from __future__ import annotations
"""TOPST_DashBoard Qt 클라이언트로 JSON payload를 broadcast하는 서버."""

import json
import socket
import threading
from typing import Any, Dict, List, Optional


QT_CLIENT_SEND_TIMEOUT_S = 0.05


class QtBroadcastServer:
    """여러 Qt 대시보드 클라이언트에 동일 payload를 전송하는 TCP 서버."""
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server_sock: Optional[socket.socket] = None
        self.clients: List[socket.socket] = []
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """수신 소켓을 열고 accept loop를 백그라운드에서 시작한다."""
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(5)
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        print(f"[zonal-test] Qt server {self.host}:{self.port}")

    def _accept_loop(self) -> None:
        """새 Qt 클라이언트를 받아 목록에 등록한다."""
        assert self.server_sock is not None
        while not self.stop_event.is_set():
            try:
                client, addr = self.server_sock.accept()
            except OSError:
                break
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            client.settimeout(QT_CLIENT_SEND_TIMEOUT_S)
            with self.lock:
                self.clients.append(client)
            print(f"[zonal-test] Qt client {addr[0]}:{addr[1]}")

    def broadcast(self, payload: Dict[str, Any]) -> None:
        """현재 연결된 모든 Qt 클라이언트에 payload를 한 줄 JSON으로 전송한다."""
        msg = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        stale: List[socket.socket] = []
        with self.lock:
            clients = list(self.clients)

        for client in clients:
            try:
                client.sendall(msg)
            except (OSError, socket.timeout):
                stale.append(client)

        if stale:
            with self.lock:
                for client in stale:
                    try:
                        client.close()
                    except OSError:
                        pass
                    if client in self.clients:
                        self.clients.remove(client)
            print(f"[zonal-test] dropped {len(stale)} stalled Qt client(s)")

    def stop(self) -> None:
        """accept loop와 모든 클라이언트 소켓을 종료한다."""
        self.stop_event.set()
        if self.server_sock is not None:
            try:
                self.server_sock.close()
            except OSError:
                pass
        with self.lock:
            for client in self.clients:
                try:
                    client.close()
                except OSError:
                    pass
            self.clients.clear()
