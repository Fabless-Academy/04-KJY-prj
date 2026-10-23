from __future__ import annotations
"""시나리오 영상 목록 관리와 Qt 선택 명령 수신 서버를 제공한다."""

import json
import os
import socket
import threading
from typing import Any, Dict, List, Optional


DEFAULT_SCENARIO_DIR = "/home/ead/zonal_architecture/AI-G/split_out"
DEFAULT_CONTROL_PORT = 10001


class ScenarioManager:
    """사용 가능한 시나리오 영상 목록과 현재 선택 상태를 관리한다."""
    def __init__(self, scenario_dir: str, fallback_video: str):
        self.lock = threading.Lock()
        self.scenario_dir = os.path.abspath(scenario_dir)
        self.fallback_video = os.path.abspath(fallback_video)
        self.videos = self._discover_videos()
        self.current_index = 0
        self.current_generation = 0
        fallback_name = os.path.basename(fallback_video)
        if self.videos:
            for index, path in enumerate(self.videos):
                if os.path.basename(path) == fallback_name or os.path.abspath(path) == os.path.abspath(fallback_video):
                    self.current_index = index
                    break
        else:
            self.videos = [os.path.abspath(fallback_video)]
        self.current_path = self.videos[self.current_index]

    def _scan_dir(self, directory: str) -> List[str]:
        """디렉터리에서 지원하는 영상 파일만 골라 절대경로로 반환한다."""
        if not os.path.isdir(directory):
            return []
        video_paths: List[str] = []
        for name in sorted(os.listdir(directory)):
            lower = name.lower()
            if lower.endswith((".mp4", ".avi", ".mov", ".mkv")):
                video_paths.append(os.path.abspath(os.path.join(directory, name)))
        return video_paths

    def _discover_videos(self) -> List[str]:
        """기본 시나리오 디렉터리와 fallback 경로를 합쳐 목록을 구성한다."""
        scanned: List[str] = []
        seen = set()
        for directory in (self.scenario_dir, os.path.dirname(self.fallback_video)):
            for path in self._scan_dir(directory):
                if path not in seen:
                    scanned.append(path)
                    seen.add(path)
        return scanned

    def snapshot(self) -> Dict[str, Any]:
        """현재 선택 상태를 thread-safe하게 읽을 수 있는 사본으로 반환한다."""
        with self.lock:
            return {
                "path": self.current_path,
                "name": os.path.basename(self.current_path),
                "index": self.current_index,
                "generation": self.current_generation,
                "list": [os.path.basename(path) for path in self.videos],
            }

    def select_by_name(self, name: str) -> bool:
        """파일 이름으로 시나리오를 선택하고 generation을 증가시킨다."""
        with self.lock:
            for index, path in enumerate(self.videos):
                if os.path.basename(path) == name:
                    if self.current_index != index:
                        self.current_index = index
                        self.current_path = path
                        self.current_generation += 1
                    return True
        return False


class ScenarioControlServer:
    """Qt에서 보내는 시나리오 선택 명령을 수신하는 간단한 TCP 서버."""
    def __init__(self, host: str, port: int, scenarios: ScenarioManager):
        self.host = host
        self.port = port
        self.scenarios = scenarios
        self.server_sock: Optional[socket.socket] = None
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """제어용 TCP 소켓을 열고 accept loop를 시작한다."""
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(5)
        self.thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.thread.start()
        print(f"[zonal-test] Scenario control {self.host}:{self.port}")

    def _accept_loop(self) -> None:
        """클라이언트 연결마다 짧은 제어 메시지를 읽고 즉시 닫는다."""
        assert self.server_sock is not None
        while not self.stop_event.is_set():
            try:
                client, _ = self.server_sock.accept()
            except OSError:
                break
            try:
                data = client.recv(4096)
                if data:
                    self._handle_payload(data)
            except OSError:
                pass
            finally:
                try:
                    client.close()
                except OSError:
                    pass

    def _handle_payload(self, data: bytes) -> None:
        """줄바꿈 기준 JSON 제어 메시지를 파싱해 시나리오를 바꾼다."""
        for raw_line in data.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                message = json.loads(line.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            if message.get("type") != "scenario/select":
                continue
            name = str(message.get("name", "")).strip()
            if not name:
                continue
            changed = self.scenarios.select_by_name(name)
            print(f"[zonal-test] scenario select '{name}' -> {'ok' if changed else 'missing'}")

    def stop(self) -> None:
        """제어 서버 소켓을 종료한다."""
        self.stop_event.set()
        if self.server_sock is not None:
            try:
                self.server_sock.close()
            except OSError:
                pass
