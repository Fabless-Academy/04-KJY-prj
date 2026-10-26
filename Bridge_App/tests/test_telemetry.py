import unittest
from unittest.mock import patch

from bev_lane_modules.telemetry import DashboardTelemetry


class DashboardTelemetryTests(unittest.TestCase):
    def test_simulated_speed_starts_at_50_kmh(self):
        telemetry = DashboardTelemetry()

        self.assertEqual(telemetry.speed_kmh, 50.0)
        self.assertEqual(telemetry.speed_target, 50.0)

    def test_simulated_speed_targets_are_bounded_between_zero_and_70(self):
        telemetry = DashboardTelemetry()

        for target in (0.0, 70.0):
            with self.subTest(target=target):
                with patch("bev_lane_modules.telemetry.random.uniform", side_effect=[target, 0.0]) as pick:
                    telemetry._pick_new_targets()

                self.assertEqual(telemetry.speed_target, target)
                self.assertEqual(pick.call_args_list[0].args, (0.0, 70.0))


if __name__ == "__main__":
    unittest.main()
