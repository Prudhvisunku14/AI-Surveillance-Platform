"""Vision Intelligence Engine — integrates detector, tracker, face recog, event engine.
Full pipeline per spec section 6."""
import os
import cv2
import time
import asyncio
import numpy as np
from datetime import datetime, timezone
from typing import List, Optional, Dict, Tuple
from app.core.config import get_settings
from app.services.detector import PersonDetector
from app.services.tracker import ByteTracker, Track
from app.services.face_recognition import get_face_service
from app.services.zone_manager import ZoneManager
from app.services.event_engine import EventDetectionEngine
from app.services.genai_service import generate_incident_summary

settings = get_settings()

# Velocity baseline for sudden movement (mu + 3sigma)
VELOCITY_BASELINE_MU = 5.0
VELOCITY_BASELINE_SIGMA = 3.0
VELOCITY_THRESHOLD = VELOCITY_BASELINE_MU + 3 * VELOCITY_BASELINE_SIGMA  # ~14 px/frame


class VisionPipeline:
    """
    Full Vision Intelligence Engine.
    Processes video frames through: detection → tracking → face recog → behavior → events.
    """

    def __init__(self, video_id: str, face_run_every_n_frames: int = 15):
        self.video_id = video_id
        self.face_run_every_n_frames = face_run_every_n_frames
        self.detector = PersonDetector()
        self.tracker = ByteTracker()
        self.face_service = get_face_service()
        self.zone_manager = ZoneManager()
        self.event_engine = EventDetectionEngine(video_id=video_id)

        self.frame_count = 0
        self.generated_events: List[dict] = []
        # Track face recognition results per track_id
        self._track_identities: Dict[int, dict] = {}
        # Track face recog attempt count
        self._face_attempts: Dict[int, int] = {}
        # Track zone dwell times {track_id: {zone_id: entry_ts}}
        self._zone_entry_ts: Dict[int, Dict[str, float]] = {}
        # Loitering event cooldown {track_id: last_event_ts}
        self._loitering_cooldown: Dict[int, float] = {}
        # Recent zone entries for tailgating {zone_id: [ts]}
        self._zone_entries: Dict[str, List[float]] = {}
        # Person appearance history for repeated reappearance
        self._person_appearances: Dict[str, List[float]] = {}

    def process_frame(self, frame: np.ndarray, frame_idx: int) -> Tuple[np.ndarray, List[dict]]:
        """
        Process one frame. Returns (annotated_frame, new_events).
        Spec: default 5 FPS processing.
        """
        self.frame_count += 1
        new_events = []

        # ── Layer 2a: YOLOv8 Detection ────────────────────────
        detections = self.detector.detect(frame)

        # ── Layer 2b: ByteTrack Tracking ──────────────────────
        active_tracks = self.tracker.update(detections)

        # ── Zone occupancy ────────────────────────────────────
        positions = [(t.centroid()) for t in active_tracks.values()]
        self.zone_manager.update_occupancy(positions)

        # ── Per-track analysis ────────────────────────────────
        for tid, track in active_tracks.items():
            cx, cy = track.centroid()
            zones = self.zone_manager.get_zones_for_point(cx, cy)
            primary_zone = zones[0] if zones else None
            zone_id = primary_zone.id if primary_zone else "Z03"
            zone_risk = primary_zone.risk_level if primary_zone else 1

            # Update zone dwell time
            if tid not in self._zone_entry_ts:
                self._zone_entry_ts[tid] = {}
            if zone_id not in self._zone_entry_ts[tid]:
                self._zone_entry_ts[tid][zone_id] = time.time()
            dwell = time.time() - self._zone_entry_ts[tid][zone_id]

            # Face recognition every N frames
            identity = self._track_identities.get(tid)
            if self.frame_count % self.face_run_every_n_frames == 0 or identity is None:
                x1, y1, x2, y2 = track.bbox
                crop = frame[max(0, y1):y2, max(0, x1):x2]
                if crop.size > 0:
                    identity = self.face_service.identify(crop, self._face_attempts.get(tid, 0))
                    self._track_identities[tid] = identity
                    self._face_attempts[tid] = self._face_attempts.get(tid, 0) + 1
                    track.person_id = identity.get("person_id")
                    track.face_confidence = identity.get("confidence", 0.0)

            if identity is None:
                identity = {"person_id": "UNKNOWN", "display_name": "Unknown",
                            "category": "Unknown", "risk_level": "High", "confidence": 0.0}

            person_id = identity.get("person_id", "UNKNOWN")
            display_name = identity.get("display_name", "Unknown")
            category = identity.get("category", "Unknown")
            risk_level = identity.get("risk_level", "High")
            confidence = identity.get("confidence", 0.0)

            # Track first appearance per person
            if person_id not in self._person_appearances:
                self._person_appearances[person_id] = []
            self._person_appearances[person_id].append(time.time())

            # ── Event: suspect_detected ──────────────────────
            if category == "Suspect" and confidence >= settings.face_similarity_threshold:
                ev = self.event_engine.check_suspect_detected(
                    tid, person_id, display_name, confidence, zone_id)
                new_events.append(ev)

            # ── Event: identity_unknown (after 3 attempts) ───
            elif confidence < settings.face_tentative_threshold:
                ev = self.event_engine.check_identity_unknown(
                    tid, zone_id, self._face_attempts.get(tid, 0))
                if ev:
                    new_events.append(ev)

            # ── Event: identity_verified ─────────────────────
            elif confidence >= settings.face_similarity_threshold and identity.get("is_known"):
                if self.frame_count % 150 == 0:  # Avoid spam
                    ev = self.event_engine.check_person_detected(
                        tid, person_id, display_name, confidence, zone_id, risk_level, zone_risk)
                    new_events.append(ev)

            # ── Event: zone_violation ────────────────────────
            if primary_zone and primary_zone.zone_type == "restricted":
                ev = self.event_engine.check_zone_violation(
                    tid, person_id, display_name, confidence, zone_id, category,
                    primary_zone.allowed_categories, zone_risk, risk_level, dwell)
                if ev and self.frame_count % 90 == 0:
                    new_events.append(ev)

            # ── Event: loitering ────────────────────────────
            cooldown = self._loitering_cooldown.get(tid, 0)
            if time.time() - cooldown > 60:  # 60s cooldown per track
                ev = self.event_engine.check_loitering(
                    tid, person_id, display_name, confidence,
                    zone_id, dwell, zone_risk, risk_level)
                if ev:
                    new_events.append(ev)
                    self._loitering_cooldown[tid] = time.time()

            # ── Event: sudden_movement ───────────────────────
            vel = track.velocity_magnitude()
            vel_score = min(vel / VELOCITY_THRESHOLD, 1.0) if VELOCITY_THRESHOLD > 0 else 0
            if vel_score >= 0.7:
                ev = self.event_engine.check_sudden_movement(
                    tid, person_id, display_name, vel_score, zone_id)
                if ev and self.frame_count % 30 == 0:
                    new_events.append(ev)

            # ── Event: repeated_reappearance ─────────────────
            appearances = self._person_appearances.get(person_id, [])
            if len(appearances) > 1 and self.frame_count % 300 == 0:
                ev = self.event_engine.check_repeated_reappearance(
                    person_id, display_name, appearances, zone_id, confidence, risk_level)
                if ev:
                    new_events.append(ev)

            # ── Track zone entry for tailgating ─────────────
            if zone_id not in self._zone_entries:
                self._zone_entries[zone_id] = []
            if primary_zone and primary_zone.zone_type == "restricted":
                now = time.time()
                self._zone_entries[zone_id].append(now)
                # Keep last 10 seconds
                self._zone_entries[zone_id] = [t for t in self._zone_entries[zone_id]
                                                if now - t < 3]
                if len(self._zone_entries[zone_id]) >= 2:
                    ev = self.event_engine.check_tailgating(
                        zone_id, list(active_tracks.keys()), 1)
                    if ev:
                        new_events.append(ev)
                        self._zone_entries[zone_id] = []  # Reset after detection

        # ── Crowd alert ────────────────────────────────────────
        crowd_alerts = self.zone_manager.get_crowd_alerts()
        for ca in crowd_alerts:
            zone = self.zone_manager.zones.get(ca["zone_id"])
            ev = self.event_engine.check_crowd_alert(
                ca["zone_id"], ca["count"], ca["max"],
                zone.risk_level if zone else 2)
            if ev and self.frame_count % 150 == 0:
                new_events.append(ev)

        # ── Annotate frame ────────────────────────────────────
        annotated = self._annotate_frame(frame, active_tracks)

        # Save snapshot for L2+ events
        for ev in new_events:
            if ev.get("severity") in ("L2", "L2+", "L3"):
                snap_path = self._save_snapshot(annotated, ev.get("event_id", "unknown"), frame_idx)
                ev["frame_snapshot_path"] = snap_path
                ev["frame_index"] = frame_idx

        # Overlay events (threat score, severity badge, event caption) on the frame
        annotated = self._overlay_events(annotated, new_events)
        return annotated, new_events

    
    def _overlay_events(self, frame: np.ndarray, events: List[dict]) -> np.ndarray:
        """Draw threat scores, severity badges and event captions on the frame.
        Expected event dict keys: 'event_type', 'threat_score', 'severity', 'frame_index'.
        """
        overlay = frame.copy()
        y_offset = 50  # start drawing event info a bit lower than person count
        for ev in events:
            etype = ev.get('event_type', '')
            threat = ev.get('threat_score', 0.0)
            severity = ev.get('severity', '')
            # Threat score text
            cv2.putText(overlay, f"Threat: {threat:.2f}", (10, y_offset),
+                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            # Severity badge (color block)
            badge_color = (0, 255, 0)  # default L1 green
+            if severity == 'L2':
+                badge_color = (0, 165, 255)  # amber
+            elif severity == 'L2+':
+                badge_color = (0, 140, 255)  # orange-like
+            elif severity == 'L3':
+                badge_color = (0, 0, 255)    # red
+            cv2.rectangle(overlay, (200, y_offset - 20), (260, y_offset + 5), badge_color, -1)
+            cv2.putText(overlay, severity, (205, y_offset),
+                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
+            # Event caption
+            cv2.putText(overlay, f"{etype}", (10, y_offset + 20),
+                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
+            y_offset += 70  # spacing for next event
+        return overlay
        """Annotate frame with bboxes, track IDs, identities.
        Colors per spec: Green=employee, Amber=visitor, Red=suspect/unknown."""
        COLORS = {
            "Employee": (0, 200, 0),    # Green
            "Visitor": (0, 165, 255),   # Amber
            "Suspect": (0, 0, 255),     # Red
            "Unknown": (0, 0, 220),     # Red-ish
        }
        annotated = frame.copy()
        for tid, track in tracks.items():
            identity = self._track_identities.get(tid, {})
            category = identity.get("category", "Unknown")
            color = COLORS.get(category, (128, 128, 128))
            x1, y1, x2, y2 = track.bbox
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"ID:{tid} {identity.get('display_name', 'Unknown')[:12]}"
            conf_label = f"Conf:{identity.get('confidence', 0):.2f}"
            cv2.putText(annotated, label, (x1, y1 - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            cv2.putText(annotated, conf_label, (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)

        # Draw zones
        annotated = self.zone_manager.draw_zones(annotated)
        # Count overlay
        cv2.putText(annotated, f"Persons: {len(tracks)}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return annotated

    def _save_snapshot(self, frame: np.ndarray, event_id: str, frame_idx: int) -> Optional[str]:
        os.makedirs(settings.frame_evidence_dir, exist_ok=True)
        path = os.path.join(settings.frame_evidence_dir, f"{event_id}_frame{frame_idx}.jpg")
        try:
            cv2.imwrite(path, frame)
            return path
        except Exception:
            return None
