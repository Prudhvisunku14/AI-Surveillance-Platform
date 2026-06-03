"""ByteTrack multi-object tracker — replaces repo CentroidTracker per spec.
Spec: track_id, first_seen_ts, last_seen_ts, bbox_history, zone_history.
Re-identification after 30 frames lost."""
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from app.core.config import get_settings

settings = get_settings()

REIDENTIFY_AFTER_FRAMES = settings.track_reidentify_after_frames  # spec: 30


@dataclass
class Track:
    """Spec: each track maintains track_id, first_seen_ts, last_seen_ts, bbox_history, zone_history."""
    track_id: int
    bbox: List[int]
    first_seen_ts: float = field(default_factory=time.time)
    last_seen_ts: float = field(default_factory=time.time)
    bbox_history: List[List[int]] = field(default_factory=list)
    zone_history: List[str] = field(default_factory=list)
    lost_frames: int = 0
    confirmed: bool = False
    hit_streak: int = 0
    person_id: Optional[str] = None
    face_confidence: float = 0.0
    velocity: Tuple[float, float] = (0.0, 0.0)
    needs_reid: bool = False         # True when lost > REIDENTIFY_AFTER_FRAMES

    def centroid(self) -> Tuple[int, int]:
        x1, y1, x2, y2 = self.bbox
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))

    def update(self, bbox: List[int]):
        prev_cx, prev_cy = self.centroid()
        self.bbox = bbox
        self.last_seen_ts = time.time()
        self.bbox_history.append(bbox)
        if len(self.bbox_history) > 50:
            self.bbox_history.pop(0)
        self.hit_streak += 1
        self.lost_frames = 0
        if self.hit_streak >= 3:
            self.confirmed = True
        cx, cy = self.centroid()
        self.velocity = (cx - prev_cx, cy - prev_cy)

    def mark_lost(self):
        self.lost_frames += 1
        self.hit_streak = 0
        if self.lost_frames >= REIDENTIFY_AFTER_FRAMES:
            self.needs_reid = True

    def add_zone(self, zone_id: str):
        if not self.zone_history or self.zone_history[-1] != zone_id:
            self.zone_history.append(zone_id)

    def duration_seconds(self) -> float:
        return self.last_seen_ts - self.first_seen_ts

    def velocity_magnitude(self) -> float:
        vx, vy = self.velocity
        return float(np.sqrt(vx**2 + vy**2))


def iou(bbox1: List[int], bbox2: List[int]) -> float:
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0


class ByteTracker:
    """ByteTrack-style IoU tracker.
    Replaces repo CentroidTracker per spec — uses bbox IoU matching like ByteTrack,
    maintains full track data structure specified."""

    HIGH_THRESH = 0.45
    LOW_THRESH = 0.25
    IOU_THRESH = 0.3
    MAX_AGE = 60

    def __init__(self):
        self.tracks: Dict[int, Track] = {}
        self._next_id = 1

    def update(self, detections: List[dict]) -> Dict[int, Track]:
        """
        detections: list of {bbox, confidence}
        Returns dict of active Track objects keyed by track_id.
        """
        # Split detections into high and low confidence (ByteTrack strategy)
        high = [d for d in detections if d["confidence"] >= self.HIGH_THRESH]
        low = [d for d in detections if self.LOW_THRESH <= d["confidence"] < self.HIGH_THRESH]

        unmatched_tracks = set(self.tracks.keys())
        matched_det_ids = set()

        # First association: high-confidence to confirmed tracks
        if high and self.tracks:
            track_ids = list(self.tracks.keys())
            cost = np.array([[1 - iou(self.tracks[tid].bbox, d["bbox"])
                              for d in high] for tid in track_ids])
            matched_r, matched_c = self._hungarian(cost, threshold=1 - self.IOU_THRESH)
            for r, c in zip(matched_r, matched_c):
                tid = track_ids[r]
                self.tracks[tid].update(high[c]["bbox"])
                unmatched_tracks.discard(tid)
                matched_det_ids.add(c)

        # Second association: low-confidence to remaining lost tracks
        remaining_tracks = [tid for tid in unmatched_tracks if self.tracks[tid].lost_frames < 5]
        unmatched_low_dets = [d for i, d in enumerate(low) if i not in matched_det_ids]
        if remaining_tracks and unmatched_low_dets:
            cost2 = np.array([[1 - iou(self.tracks[tid].bbox, d["bbox"])
                               for d in unmatched_low_dets] for tid in remaining_tracks])
            r2, c2 = self._hungarian(cost2, threshold=1 - self.IOU_THRESH)
            matched_r2 = set()
            for r, c in zip(r2, c2):
                tid = remaining_tracks[r]
                self.tracks[tid].update(unmatched_low_dets[c]["bbox"])
                unmatched_tracks.discard(tid)
                matched_r2.add(r)

        # Mark unmatched tracks as lost
        for tid in list(unmatched_tracks):
            self.tracks[tid].mark_lost()
            if self.tracks[tid].lost_frames > self.MAX_AGE:
                del self.tracks[tid]

        # Create new tracks for unmatched high-confidence detections
        unmatched_new = [d for i, d in enumerate(high) if i not in matched_det_ids]
        for d in unmatched_new:
            t = Track(track_id=self._next_id, bbox=d["bbox"])
            t.bbox_history.append(d["bbox"])
            self.tracks[self._next_id] = t
            self._next_id += 1

        return {tid: t for tid, t in self.tracks.items() if t.confirmed or t.hit_streak >= 1}

    def _hungarian(self, cost: np.ndarray, threshold: float):
        """Simple greedy matching (full Hungarian too expensive for small N)."""
        from scipy.optimize import linear_sum_assignment
        if cost.size == 0:
            return [], []
        row_ind, col_ind = linear_sum_assignment(cost)
        valid_r, valid_c = [], []
        for r, c in zip(row_ind, col_ind):
            if cost[r, c] <= threshold:
                valid_r.append(r)
                valid_c.append(c)
        return valid_r, valid_c
