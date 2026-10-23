from __future__ import annotations
"""실데이터가 없을 때 계기판 시연용 telemetry를 생성한다."""

import math
import random
import time
from typing import Dict


class DashboardTelemetry:
    """Qt 계기판 시연용으로 천천히 변하는 telemetry를 생성한다."""

    def __init__(self):
        self.speed_kmh = 96.0
        self.speed_target = 96.0
        self.rpm = 2200.0
        self.rpm_target = 2200.0
        self.fuel_l = 820.0
        self.last_target_update = time.time()
        self.target_interval_s = 3.5

    def _pick_new_targets(self) -> None:
        """다음 구간에서 서서히 수렴할 목표 speed와 rpm 값을 정한다."""
        self.speed_target = random.uniform(80.0, 160.0)
        self.rpm_target = max(
            900.0,
            min(5200.0, 900.0 + self.speed_target * 30.0 + random.uniform(-120.0, 120.0)),
        )

    def update(self, frame_index: int) -> Dict[str, float]:
        """목표값을 기준으로 speed, rpm, fuel을 완만하게 갱신한다."""
        now = time.time()
        if now - self.last_target_update >= self.target_interval_s:
            self._pick_new_targets()
            self.last_target_update = now

        self.speed_kmh += (self.speed_target - self.speed_kmh) * 0.06
        self.rpm += (self.rpm_target - self.rpm) * 0.08
        self.fuel_l = max(
            320.0,
            min(980.0, self.fuel_l - 0.015 + 0.004 * math.sin(float(frame_index) * 0.02)),
        )

        return {
            "speed_kmh": float(self.speed_kmh),
            "rpm": float(self.rpm),
            "fuel_l": float(self.fuel_l),
        }
