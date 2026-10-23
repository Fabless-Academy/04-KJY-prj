from __future__ import annotations
"""프레임 간 lane, object, steering smoothing 상태를 유지한다."""

import threading
from typing import Any, Dict, List, Tuple


def smooth_lane_points(
    previous: List[Dict[str, int]],
    current: List[Dict[str, int]],
    alpha: float,
) -> List[Dict[str, int]]:
    """동일 길이의 두 차선 point 목록을 지수평활로 섞는다."""
    if not previous or len(previous) != len(current):
        return [dict(point) for point in current]

    smoothed: List[Dict[str, int]] = []
    for prev, curr in zip(previous, current):
        smoothed.append(
            {
                "x": int(round(alpha * prev["x"] + (1.0 - alpha) * curr["x"])),
                "y": int(round(alpha * prev["y"] + (1.0 - alpha) * curr["y"])),
            }
        )
    return smoothed


def smooth_lane_set(
    previous_set: List[List[Dict[str, int]]],
    current_set: List[List[Dict[str, int]]],
    alpha: float,
) -> List[List[Dict[str, int]]]:
    """최대 4개 차선 슬롯 각각에 lane smoothing을 적용한다."""
    smoothed_set: List[List[Dict[str, int]]] = [[], [], [], []]
    for lane_idx in range(4):
        previous = previous_set[lane_idx] if lane_idx < len(previous_set) else []
        current = current_set[lane_idx] if lane_idx < len(current_set) else []
        smoothed_set[lane_idx] = smooth_lane_points(previous, current, alpha)
    return smoothed_set


def _smooth_object(previous: Dict[str, Any], current: Dict[str, Any], alpha: float) -> Dict[str, Any]:
    """같은 track_id 객체의 BEV 좌표를 부드럽게 이어준다."""
    smoothed = dict(current)
    smoothed["bev_x"] = alpha * float(previous.get("bev_x", 0.0)) + (1.0 - alpha) * float(current.get("bev_x", 0.0))
    smoothed["bev_y"] = alpha * float(previous.get("bev_y", 0.0)) + (1.0 - alpha) * float(current.get("bev_y", 0.0))
    smoothed["track_id"] = int(previous.get("track_id", 0))
    return smoothed


def _safe_track_id(value: Any) -> int:
    """track_id를 안전하게 int로 변환하고 실패 시 -1을 반환한다."""
    try:
        if value is None:
            return -1
        return int(value)
    except (TypeError, ValueError):
        return -1


class BevLaneState:
    """브리지 실행 중 유지되는 lane, object, steering 내부 상태 저장소."""
    def __init__(self):
        self.lock = threading.Lock()
        self.smoothed_lanes: List[List[Dict[str, int]]] = [[], [], [], []]
        self.object_tracks: List[Dict[str, Any]] = []
        self.next_track_id = 1
        self.smoothed_steering_deg = 0.0
        self.ego_pair_center_x: float = 0.0
        self.ego_pair_valid = False

    def smooth(self, lanes: List[List[Dict[str, int]]], alpha: float) -> List[List[Dict[str, int]]]:
        """lane smoothing 상태를 갱신하고 외부에는 사본을 반환한다."""
        with self.lock:
            self.smoothed_lanes = smooth_lane_set(self.smoothed_lanes, lanes, alpha)
            return [[dict(point) for point in lane] for lane in self.smoothed_lanes]

    def smooth_steering(self, steering_deg: float, alpha: float) -> float:
        """steering 값을 지수평활해 급격한 튐을 줄인다."""
        with self.lock:
            self.smoothed_steering_deg = alpha * self.smoothed_steering_deg + (1.0 - alpha) * steering_deg
            return self.smoothed_steering_deg

    def get_ego_pair_center(self) -> Tuple[bool, float]:
        """이전 프레임의 ego 차선 중심 추정값을 읽는다."""
        with self.lock:
            return self.ego_pair_valid, self.ego_pair_center_x

    def update_ego_pair_center(self, center_x: float, alpha: float = 0.85) -> float:
        """ego 차선 중심 x를 프레임 간 smoothing하며 갱신한다."""
        with self.lock:
            if not self.ego_pair_valid:
                self.ego_pair_center_x = float(center_x)
                self.ego_pair_valid = True
            else:
                self.ego_pair_center_x = alpha * self.ego_pair_center_x + (1.0 - alpha) * float(center_x)
            return self.ego_pair_center_x

    def update_object_tracks(
        self,
        objects: List[Dict[str, Any]],
        _max_distance: float,
        _confirm_frames: int,
        _miss_frames: int,
        _alpha: float,
        max_objects: int,
    ) -> List[Dict[str, Any]]:
        """객체 목록을 track_id 기준으로 smoothing과 hold 처리해 게시용 목록을 만든다."""
        confirm_frames = max(1, int(_confirm_frames))
        miss_frames = max(0, int(_miss_frames))
        alpha = max(0.0, min(0.98, float(_alpha)))

        with self.lock:
            detections = [dict(obj) for obj in objects]
            tracks_by_id = {
                _safe_track_id(track.get("track_id", -1)): track
                for track in self.object_tracks
                if _safe_track_id(track.get("track_id", -1)) >= 0
            }
            updated_tracks: List[Dict[str, Any]] = []
            seen_ids = set()

            for detection in detections:
                # track_id가 없으면 새 track으로 간주해 내부 ID를 발급한다.
                track_id = _safe_track_id(detection.get("track_id", -1))
                if track_id < 0:
                    new_track = dict(detection)
                    new_track["track_id"] = self.next_track_id
                    new_track["hits"] = 1
                    new_track["misses"] = 0
                    self.next_track_id += 1
                    updated_tracks.append(new_track)
                    continue

                seen_ids.add(track_id)
                previous_track = tracks_by_id.get(track_id)
                if previous_track is None:
                    new_track = dict(detection)
                    new_track["hits"] = 1
                    new_track["misses"] = 0
                    updated_tracks.append(new_track)
                    continue

                smoothed_track = _smooth_object(previous_track, detection, alpha)
                smoothed_track["cls"] = detection.get("cls", previous_track.get("cls"))
                smoothed_track["score"] = detection.get("score", previous_track.get("score"))
                smoothed_track["lane_id"] = detection.get("lane_id", previous_track.get("lane_id"))
                smoothed_track["hits"] = int(previous_track.get("hits", 0)) + 1
                smoothed_track["misses"] = 0
                updated_tracks.append(smoothed_track)

            for track in self.object_tracks:
                track_id = _safe_track_id(track.get("track_id", -1))
                if track_id in seen_ids:
                    continue
                misses = int(track.get("misses", 0)) + 1
                if misses > miss_frames:
                    continue
                carried = dict(track)
                carried["misses"] = misses
                updated_tracks.append(carried)

            self.object_tracks = updated_tracks

            published = []
            for track in self.object_tracks:
                if int(track.get("hits", 0)) < confirm_frames:
                    continue
                item = dict(track)
                item.pop("hits", None)
                item.pop("misses", None)
                published.append(item)

            published.sort(key=lambda obj: float(obj.get("bev_y", -1e9)), reverse=True)
            if max_objects > 0:
                published = published[:max_objects]
            return published
