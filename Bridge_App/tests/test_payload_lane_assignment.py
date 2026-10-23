import unittest

import numpy as np

from bev_lane_modules.payload import _assign_object_lane_id, build_object_payload


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


if __name__ == "__main__":
    unittest.main()
