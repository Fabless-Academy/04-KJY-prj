import unittest

import numpy as np

from bev_lane_modules.geometry import fit_lane_curve
from bev_lane_modules.payload import _assign_object_lane_id, build_lane_outputs, build_object_payload
from bev_lane_modules.state import BevLaneState


class ObjectLaneAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.lanes = [
            [{"x": x, "y": y} for y in (0, 600)]
            for x in (100, 200, 300, 400)
        ]

    def test_object_inside_ego_lane_corridor_is_assigned_to_ego_lane(self):
        lane_id = _assign_object_lane_id(
            {"bev_x": 250, "bev_y": 500},
            self.lanes,
        )
        self.assertEqual(lane_id, 1)

    def test_object_outside_all_corridors_is_not_forced_into_nearest_lane(self):
        lane_id = _assign_object_lane_id(
            {"bev_x": 450, "bev_y": 500},
            self.lanes,
        )
        self.assertIsNone(lane_id)

    def test_unassigned_object_does_not_keep_stale_ego_lane_id(self):
        payload = build_object_payload(
            result={
                "width": 800,
                "height": 600,
                "objects": [
                    {
                        "x_min": 440,
                        "x_max": 460,
                        "y_max": 500,
                        "lane_id": 1,
                    }
                ],
            },
            homography=np.eye(3),
            bev_width=800,
            bev_height=600,
            source_width=800,
            source_height=600,
            correction=None,
            include_objects=True,
            max_objects=10,
            lane_state=None,
            object_track_distance=60.0,
            object_track_confirm=1,
            object_track_miss=0,
            object_track_alpha=0.7,
            qt_lanes=self.lanes,
        )
        self.assertIsNone(payload["bev_objects"][0]["lane_id"])

    def test_all_detected_lines_are_preserved_separately_from_ego_slots(self):
        result = {
            "width": 1000,
            "height": 720,
            "lanes": [
                {"points": [{"x": x, "y": 100}, {"x": x, "y": 700}], "score": 0.9}
                for x in (100, 200, 300, 400, 500, 600)
            ],
        }

        ego_slots, all_lines = build_lane_outputs(
            result=result,
            homography=np.eye(3),
            bev_width=1000,
            bev_height=720,
            source_width=1000,
            source_height=720,
            correction=None,
            lane_fit_degree=0,
            lane_fit_samples=24,
            lane_fit_min_points=4,
            lane_top_ratio=0.12,
            lane_bottom_ratio=0.97,
            lane_state=None,
            lane_smoothing=0.88,
        )

        self.assertEqual(sum(bool(lane) for lane in ego_slots), 4)
        self.assertEqual(len(all_lines), 6)
        self.assertEqual(
            [round(sum(point["x"] for point in lane) / len(lane)) for lane in all_lines],
            [100, 200, 300, 400, 500, 600],
        )

    def test_lane_fit_does_not_extrapolate_outside_detected_y_range(self):
        points = [
            {"x": 200, "y": 80},
            {"x": 250, "y": 60},
            {"x": 300, "y": 40},
            {"x": 350, "y": 20},
        ]
        fitted = fit_lane_curve(
            points,
            degree=2,
            sample_count=24,
            min_points=4,
            top_y=10,
            bottom_y=100,
        )

        self.assertEqual(min(point["y"] for point in fitted), 20)
        self.assertEqual(max(point["y"] for point in fitted), 80)

    def test_lane_smoothing_matches_by_position_when_detection_count_changes(self):
        state = BevLaneState()
        previous = [
            [{"x": x, "y": 700}, {"x": x, "y": 100}]
            for x in (100, 300, 500)
        ]
        current = [
            [{"x": x, "y": 700}, {"x": x, "y": 100}]
            for x in (300, 500)
        ]

        state.smooth_detected_lanes(previous, alpha=0.88, bev_width=1000)
        smoothed = state.smooth_detected_lanes(current, alpha=0.88, bev_width=1000)

        self.assertEqual([lane[0]["x"] for lane in smoothed], [300, 500])

    def test_ego_slots_reuse_the_same_smoothed_lines_as_dashboard_output(self):
        state = BevLaneState()
        result = {
            "width": 1000,
            "height": 720,
            "lanes": [
                {"points": [{"x": x, "y": 100}, {"x": x, "y": 700}], "score": 0.9}
                for x in (100, 300, 500, 700)
            ],
        }

        state.smooth_detected_lanes(
            [
                [{"x": x - 20, "y": 100}, {"x": x - 20, "y": 700}]
                for x in (100, 300, 500, 700)
            ],
            alpha=0.88,
            bev_width=1000,
        )
        ego_slots, all_lines = build_lane_outputs(
            result=result,
            homography=np.eye(3),
            bev_width=1000,
            bev_height=720,
            source_width=1000,
            source_height=720,
            correction=None,
            lane_fit_degree=0,
            lane_fit_samples=24,
            lane_fit_min_points=4,
            lane_top_ratio=0.12,
            lane_bottom_ratio=0.97,
            lane_state=state,
            lane_smoothing=0.88,
        )

        self.assertTrue(all(line in all_lines for line in ego_slots if line))


if __name__ == "__main__":
    unittest.main()
