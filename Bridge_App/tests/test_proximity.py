import unittest

from bev_lane_modules.proximity import calculate_bev_speed_recommendation


class BevSpeedRecommendationTests(unittest.TestCase):
    def setUp(self):
        self.height = 720

    def test_no_ego_lane_detection_uses_maximum_distance_target(self):
        result = calculate_bev_speed_recommendation(
            [{"lane_id": 0, "bev_y": 700}],
            self.height,
            0.82,
            0.96,
        )
        self.assertEqual(result["proximity_status"], "no_ego_lane_object")
        self.assertEqual(result["recommended_speed_kmh"], 100.0)

    def test_clear_object_uses_maximum_distance_target(self):
        result = calculate_bev_speed_recommendation(
            [{"lane_id": 1, "bev_y": 500}],
            self.height,
            0.82,
            0.96,
        )
        self.assertEqual(result["proximity_status"], "clear")
        self.assertEqual(result["recommended_speed_kmh"], 100.0)

    def test_object_between_thresholds_reduces_speed_linearly(self):
        result = calculate_bev_speed_recommendation(
            [{"lane_id": 1, "bev_y": 0.89 * self.height}],
            self.height,
            0.82,
            0.96,
        )
        self.assertEqual(result["proximity_status"], "slowing")
        self.assertAlmostEqual(result["recommended_speed_kmh"], 50.0)

    def test_object_at_stop_threshold_recommends_zero(self):
        result = calculate_bev_speed_recommendation(
            [{"lane_id": 1, "bev_y": 0.97 * self.height}],
            self.height,
            0.82,
            0.96,
        )
        self.assertEqual(result["proximity_status"], "stop")
        self.assertEqual(result["recommended_speed_kmh"], 0.0)

    def test_invalid_thresholds_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_bev_speed_recommendation([], self.height, 0.96, 0.82)


if __name__ == "__main__":
    unittest.main()
