from __future__ import annotations
"""VCP/MICOM 제어값 변환과 IPC 송신 래퍼를 제공한다."""

import time
from typing import Optional


IPC_PATH = "/dev/tcc_ipc_micom"
CMD_WHEEL = 0x103
CMD_MOTOR = 0x104
CMD_EMER_SIGNAL = 0x101
MAX_SPEED_COMMAND = 0x64
EMER_SIGNAL_ON = 0x01
EMER_SIGNAL_OFF = 0x02

STR_MIN, STR_MID, STR_MAX = 92, 66, 42
AUTO_STEER_LIMIT = 14.0

try:
    from Library.IPC_Library import IPC_SendPacketWithIPCHeader
except ImportError:
    def IPC_SendPacketWithIPCHeader(file, type, id, cmd, payload):
        pass


def steer_to_servo(sdeg_clamped: float) -> int:
    """조향각(도)을 보드가 기대하는 1바이트 servo 값으로 변환한다."""
    if sdeg_clamped >= 0:
        return round(STR_MID + sdeg_clamped * (STR_MAX - STR_MID) / AUTO_STEER_LIMIT)
    return round(STR_MID + sdeg_clamped * (STR_MID - STR_MIN) / AUTO_STEER_LIMIT)


def speed_to_bytes(speed_kmh: float) -> bytes:
    """속도 값을 정수부/소수부 2바이트 형식으로 인코딩한다."""
    speed = max(0.0, min(127.0, float(speed_kmh)))
    speed_int = int(speed)
    speed_frac = int((speed - speed_int) * 256)
    return bytes([speed_int, speed_frac])


class IpcSender:
    """속도/조향값을 주기적으로 MICOM IPC로 내보내는 송신기."""
    def __init__(self, enabled: bool, ipc_path: str, period_ms: int):
        self.enabled = enabled
        self.ipc_path = ipc_path
        self.period_s = max(0.001, float(period_ms) / 1000.0)
        self.handle = None
        self.last_send_ts = 0.0
        self.last_speed_bytes: Optional[bytes] = None
        self.last_emergency_signal_active: Optional[bool] = None

    def start(self) -> None:
        """제어가 활성화된 경우 IPC 디바이스를 연다."""
        if not self.enabled:
            return
        self.handle = open(self.ipc_path, "wb")
        print(f"[zonal-test] IPC connected {self.ipc_path}")

    def stop(self) -> None:
        """열어 둔 IPC 핸들을 닫는다."""
        if self.handle is not None:
            try:
                self.handle.close()
            except OSError:
                pass
            self.handle = None

    def send(self, speed_command: float, steering_deg: float, emergency_signal_active: bool) -> None:
        """주기 제한을 지키면서 속도/조향 및 비상등 상태 명령을 전송한다."""
        if self.handle is None:
            return
        now = time.time()
        if now - self.last_send_ts < self.period_s:
            return

        servo = steer_to_servo(max(-AUTO_STEER_LIMIT, min(AUTO_STEER_LIMIT, steering_deg)))
        IPC_SendPacketWithIPCHeader(self.handle, 1, 0, CMD_WHEEL, servo.to_bytes(1, "big"))

        speed_bytes = speed_to_bytes(speed_command)
        if speed_bytes != self.last_speed_bytes:
            IPC_SendPacketWithIPCHeader(self.handle, 1, 0, CMD_MOTOR, speed_bytes)
            self.last_speed_bytes = speed_bytes

        if emergency_signal_active != self.last_emergency_signal_active:
            emergency_signal_data = bytes(
                [EMER_SIGNAL_ON if emergency_signal_active else EMER_SIGNAL_OFF]
            )
            IPC_SendPacketWithIPCHeader(
                self.handle,
                1,
                0,
                CMD_EMER_SIGNAL,
                emergency_signal_data,
            )
            self.last_emergency_signal_active = emergency_signal_active
        self.last_send_ts = now
