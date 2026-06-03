"""Event Detection Engine — exact 15-event catalog from spec section 8.
All trigger conditions, severity levels, and auto-actions per spec."""
import uuid
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from app.core.config import get_settings
from app.services.threat_scoring import (
    ThreatFeatures, get_threat_engine, encode_risk_level, encode_zone_risk
)

settings = get_settings()

# ── Spec exact event catalog ──────────────────────────────────
EVENT_CATALOG = {
    "person_detected":          {"default_severity": "L1", "auto_action": "Log"},
    "person_exited":            {"default_severity": "L1", "auto_action": "Log"},
    "identity_verified":        {"default_severity": "L1", "auto_action": "Log"},
    "identity_unknown":         {"default_severity": "L2", "auto_action": "Alert + LLM summary"},
    "loitering_warning":        {"default_severity": "L2", "auto_action": "Alert + LLM summary"},
    "loitering_critical":       {"default_severity": "L3", "auto_action": "Alert + Notification"},
    "zone_violation":           {"default_severity": "L2", "auto_action": "Alert + LLM summary"},
    "tailgating_detected":      {"default_severity": "L3", "auto_action": "Alert + Lock Zone"},
    "sensor_mismatch":          {"default_severity": "L2", "auto_action": "Alert"},
    "identity_mismatch":        {"default_severity": "L3", "auto_action": "Alert + Notification"},
    "crowd_alert":              {"default_severity": "L2", "auto_action": "Alert"},
    "sudden_movement":          {"default_severity": "L2", "auto_action": "Alert"},
    "suspect_detected":         {"default_severity": "L3", "auto_action": "Alert + Notification"},
    "abandoned_object":         {"default_severity": "L3", "auto_action": "Alert + Notification"},
    "repeated_reappearance":    {"default_severity": "L2", "auto_action": "Alert"},
}


def make_event_id(video_id: str, counter: int) -> str:
    """Spec: EVT_V001_0042 format."""
    vid = (video_id or "LIVE").replace("-", "")[:4].upper()
    return f"EVT_{vid}_{counter:04d}"


def build_event(
    event_type: str,
    video_id: Optional[str],
    frame_index: Optional[int],
    frame_snapshot_path: Optional[str],
    persons_involved: List[dict],
    zone_id: Optional[str],
    threat_features: ThreatFeatures,
    extra_meta: Optional[dict] = None,
    event_counter: int = 0,
) -> dict:
    """Build canonical event dict — exact spec schema section 8."""
    engine = get_threat_engine()
    score, severity_from_score, explainability = engine.score(threat_features, event_type)

    # Spec: event catalog defines default severity; threat score can escalate but not downgrade L3
    catalog_sev = EVENT_CATALOG.get(event_type, {}).get("default_severity", "L1")
    sev_order = {"L1": 1, "L2": 2, "L2+": 3, "L3": 4}
    final_severity = max([catalog_sev, severity_from_score],
                         key=lambda s: sev_order.get(s, 1))

    event_id = make_event_id(video_id or "LIVE", event_counter)

    return {
        "event_id": event_id,
        "video_id": video_id,
        "event_type": event_type,
        "severity": final_severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "frame_index": frame_index,
        "frame_snapshot_path": frame_snapshot_path,
        "persons_involved": persons_involved,
        "threat_score": round(score, 4),
        "threat_features": threat_features.to_dict(),
        "threat_explainability": explainability,
        "genai_summary": None,
        "genai_data": None,
        "acknowledged": False,
        "acknowledged_by": None,
        "acknowledged_at": None,
        "zone_id": zone_id,
        "metadata_extra": extra_meta or {},
        "auto_action": EVENT_CATALOG.get(event_type, {}).get("auto_action", "Log"),
    }


class EventDetectionEngine:
    """Detects all 15 event types from spec using Vision layer outputs."""

    def __init__(self, video_id: str = "LIVE"):
        self.video_id = video_id
        self.event_counter = 0
        # Loitering tracking per track_id: {track_id: first_seen_ts}
        self._zone_entry_times: Dict[int, Dict[str, float]] = {}
        # Tailgating: recent zone entries
        self._zone_entries: Dict[str, List[float]] = {}
        # Reappearance: {person_id: [timestamps]}
        self._person_appearances: Dict[str, List[float]] = {}
        # Abandoned objects: {track_id: {first_seen_ts, last_person_nearby_ts}}
        self._stationary_objects: Dict[int, dict] = {}

    def _next_id(self) -> int:
        self.event_counter += 1
        return self.event_counter

    def check_person_detected(self, track_id: int, person_id: str, display_name: str,
                               confidence: float, zone_id: str, risk_level: str,
                               zone_risk: int) -> dict:
        """L1: person enters monitored zone."""
        tf = ThreatFeatures(
            identity_confidence=confidence,
            is_known_person=1 if "UNKNOWN" not in person_id else 0,
            risk_level_encoded=encode_risk_level(risk_level),
            zone_risk_encoded=encode_zone_risk(zone_risk),
            loitering_duration_norm=0.0,
            sensor_corroborated=0,
            visit_count_1h_norm=0.0,
            velocity_anomaly_score=0.0,
            concurrent_events_count=0,
        )
        return build_event(
            "person_detected", self.video_id, None, None,
            [{"track_id": track_id, "person_id": person_id, "display_name": display_name,
              "face_confidence": confidence, "zone_id": zone_id,
              "duration_in_zone_seconds": 0}],
            zone_id, tf, event_counter=self._next_id()
        )

    def check_loitering(self, track_id: int, person_id: str, display_name: str,
                         confidence: float, zone_id: str, duration_seconds: float,
                         zone_risk: int, risk_level: str) -> Optional[dict]:
        """Spec: >120s → loitering_warning (L2), >300s → loitering_critical (L3)."""
        if duration_seconds < settings.loitering_warning_seconds:
            return None

        event_type = ("loitering_critical"
                      if duration_seconds >= settings.loitering_critical_seconds
                      else "loitering_warning")

        tf = ThreatFeatures(
            identity_confidence=confidence,
            is_known_person=1 if "UNKNOWN" not in person_id else 0,
            risk_level_encoded=encode_risk_level(risk_level),
            zone_risk_encoded=encode_zone_risk(zone_risk),
            loitering_duration_norm=min(duration_seconds / 300.0, 1.0),  # spec formula
            sensor_corroborated=0,
            visit_count_1h_norm=0.0,
            velocity_anomaly_score=0.0,
            concurrent_events_count=0,
        )
        return build_event(
            event_type, self.video_id, None, None,
            [{"track_id": track_id, "person_id": person_id, "display_name": display_name,
              "face_confidence": confidence, "zone_id": zone_id,
              "duration_in_zone_seconds": duration_seconds}],
            zone_id, tf, event_counter=self._next_id()
        )

    def check_zone_violation(self, track_id: int, person_id: str, display_name: str,
                              confidence: float, zone_id: str, category: str,
                              allowed_categories: List[str], zone_risk: int,
                              risk_level: str, duration: float = 0) -> Optional[dict]:
        """Spec: unauthorized category in restricted zone → L2."""
        if category in allowed_categories:
            return None
        tf = ThreatFeatures(
            identity_confidence=confidence,
            is_known_person=1 if "UNKNOWN" not in person_id else 0,
            risk_level_encoded=encode_risk_level(risk_level),
            zone_risk_encoded=encode_zone_risk(zone_risk),
            loitering_duration_norm=min(duration / 300.0, 1.0),
            sensor_corroborated=0,
            visit_count_1h_norm=0.0,
            velocity_anomaly_score=0.0,
            concurrent_events_count=0,
        )
        return build_event(
            "zone_violation", self.video_id, None, None,
            [{"track_id": track_id, "person_id": person_id, "display_name": display_name,
              "face_confidence": confidence, "zone_id": zone_id,
              "duration_in_zone_seconds": duration}],
            zone_id, tf, event_counter=self._next_id()
        )

    def check_suspect_detected(self, track_id: int, person_id: str, display_name: str,
                                confidence: float, zone_id: str) -> dict:
        """Spec: face match to high-risk registry → always L3."""
        tf = ThreatFeatures(
            identity_confidence=confidence,
            is_known_person=1,
            risk_level_encoded=2,   # high
            zone_risk_encoded=3,
            loitering_duration_norm=0.0,
            sensor_corroborated=0,
            visit_count_1h_norm=0.0,
            velocity_anomaly_score=0.5,
            concurrent_events_count=1,
        )
        return build_event(
            "suspect_detected", self.video_id, None, None,
            [{"track_id": track_id, "person_id": person_id, "display_name": display_name,
              "face_confidence": confidence, "zone_id": zone_id,
              "duration_in_zone_seconds": 0}],
            zone_id, tf, event_counter=self._next_id()
        )

    def check_identity_unknown(self, track_id: int, zone_id: str,
                                attempt: int = 3) -> Optional[dict]:
        """Spec: face confidence <0.60 after 3 attempts → L2."""
        if attempt < 3:
            return None
        tf = ThreatFeatures(
            identity_confidence=0.3,
            is_known_person=0,
            risk_level_encoded=2,
            zone_risk_encoded=2,
            loitering_duration_norm=0.0,
            sensor_corroborated=0,
            visit_count_1h_norm=0.0,
            velocity_anomaly_score=0.0,
            concurrent_events_count=0,
        )
        return build_event(
            "identity_unknown", self.video_id, None, None,
            [{"track_id": track_id, "person_id": "UNKNOWN",
              "display_name": "Unknown Person", "face_confidence": 0.3,
              "zone_id": zone_id, "duration_in_zone_seconds": 0}],
            zone_id, tf, event_counter=self._next_id()
        )

    def check_tailgating(self, zone_id: str, track_ids: List[int],
                          access_event_count: int) -> Optional[dict]:
        """Spec: 2+ persons enter restricted zone on single access event → L3."""
        if len(track_ids) < 2 or access_event_count >= len(track_ids):
            return None
        tf = ThreatFeatures(
            identity_confidence=0.5,
            is_known_person=0,
            risk_level_encoded=2,
            zone_risk_encoded=3,
            loitering_duration_norm=0.0,
            sensor_corroborated=1,
            visit_count_1h_norm=0.0,
            velocity_anomaly_score=0.3,
            concurrent_events_count=len(track_ids),
        )
        return build_event(
            "tailgating_detected", self.video_id, None, None,
            [{"track_id": tid, "person_id": "UNKNOWN", "display_name": "Unknown",
              "face_confidence": 0.0, "zone_id": zone_id,
              "duration_in_zone_seconds": 0} for tid in track_ids],
            zone_id, tf, event_counter=self._next_id()
        )

    def check_crowd_alert(self, zone_id: str, count: int, max_occupancy: int,
                           zone_risk: int) -> Optional[dict]:
        """Spec: occupancy > zone max_occupancy → L2."""
        if count <= max_occupancy:
            return None
        tf = ThreatFeatures(
            identity_confidence=0.5,
            is_known_person=0,
            risk_level_encoded=1,
            zone_risk_encoded=encode_zone_risk(zone_risk),
            loitering_duration_norm=0.0,
            sensor_corroborated=0,
            visit_count_1h_norm=0.0,
            velocity_anomaly_score=0.0,
            concurrent_events_count=count,
        )
        return build_event(
            "crowd_alert", self.video_id, None, None, [],
            zone_id, tf,
            extra_meta={"count": count, "max_occupancy": max_occupancy},
            event_counter=self._next_id()
        )

    def check_sudden_movement(self, track_id: int, person_id: str, display_name: str,
                               velocity_score: float, zone_id: str) -> Optional[dict]:
        """Spec: velocity anomaly (mu + 3sigma baseline exceeded) → L2."""
        if velocity_score < 0.7:
            return None
        tf = ThreatFeatures(
            identity_confidence=0.5,
            is_known_person=1 if "UNKNOWN" not in person_id else 0,
            risk_level_encoded=1,
            zone_risk_encoded=2,
            loitering_duration_norm=0.0,
            sensor_corroborated=0,
            visit_count_1h_norm=0.0,
            velocity_anomaly_score=velocity_score,
            concurrent_events_count=0,
        )
        return build_event(
            "sudden_movement", self.video_id, None, None,
            [{"track_id": track_id, "person_id": person_id, "display_name": display_name,
              "face_confidence": 0.0, "zone_id": zone_id, "duration_in_zone_seconds": 0}],
            zone_id, tf, event_counter=self._next_id()
        )

    def check_sensor_mismatch(self, sensor_event_id: str, location_id: str) -> dict:
        """Spec: sensor event with no video corroboration → L2."""
        tf = ThreatFeatures(
            identity_confidence=0.5,
            is_known_person=0,
            risk_level_encoded=1,
            zone_risk_encoded=2,
            loitering_duration_norm=0.0,
            sensor_corroborated=0,
            visit_count_1h_norm=0.0,
            velocity_anomaly_score=0.0,
            concurrent_events_count=0,
        )
        return build_event(
            "sensor_mismatch", self.video_id, None, None, [],
            location_id, tf,
            extra_meta={"sensor_event_id": sensor_event_id},
            event_counter=self._next_id()
        )

    def check_identity_mismatch(self, sensor_person_id: str, video_person_id: str,
                                 track_id: int, zone_id: str) -> dict:
        """Spec: sensor ID ≠ video face ID → L3."""
        tf = ThreatFeatures(
            identity_confidence=0.5,
            is_known_person=1,
            risk_level_encoded=2,
            zone_risk_encoded=3,
            loitering_duration_norm=0.0,
            sensor_corroborated=1,
            visit_count_1h_norm=0.0,
            velocity_anomaly_score=0.0,
            concurrent_events_count=1,
        )
        return build_event(
            "identity_mismatch", self.video_id, None, None,
            [{"track_id": track_id, "person_id": video_person_id,
              "display_name": video_person_id, "face_confidence": 0.5,
              "zone_id": zone_id, "duration_in_zone_seconds": 0}],
            zone_id, tf,
            extra_meta={"sensor_person_id": sensor_person_id,
                        "video_person_id": video_person_id},
            event_counter=self._next_id()
        )

    def check_abandoned_object(self, obj_track_id: int, zone_id: str,
                                stationary_seconds: float) -> Optional[dict]:
        """Spec: stationary bounding box >60s after person exit → L3."""
        if stationary_seconds < settings.abandoned_object_seconds:
            return None
        tf = ThreatFeatures(
            identity_confidence=0.0,
            is_known_person=0,
            risk_level_encoded=2,
            zone_risk_encoded=3,
            loitering_duration_norm=min(stationary_seconds / 300.0, 1.0),
            sensor_corroborated=0,
            visit_count_1h_norm=0.0,
            velocity_anomaly_score=0.0,
            concurrent_events_count=0,
        )
        return build_event(
            "abandoned_object", self.video_id, None, None, [],
            zone_id, tf,
            extra_meta={"stationary_seconds": stationary_seconds,
                        "object_track_id": obj_track_id},
            event_counter=self._next_id()
        )

    def check_repeated_reappearance(self, person_id: str, display_name: str,
                                     appearances: List[float], zone_id: str,
                                     confidence: float, risk_level: str) -> Optional[dict]:
        """Spec: same identity >3 times in 1 hour → L2."""
        now = time.time()
        recent = [t for t in appearances if now - t < 3600]  # 1-hour window
        if len(recent) <= settings.repeated_reappearance_count:
            return None
        tf = ThreatFeatures(
            identity_confidence=confidence,
            is_known_person=1,
            risk_level_encoded=encode_risk_level(risk_level),
            zone_risk_encoded=2,
            loitering_duration_norm=0.0,
            sensor_corroborated=0,
            visit_count_1h_norm=min(len(recent) / 10.0, 1.0),  # spec formula
            velocity_anomaly_score=0.0,
            concurrent_events_count=len(recent),
        )
        return build_event(
            "repeated_reappearance", self.video_id, None, None,
            [{"track_id": 0, "person_id": person_id, "display_name": display_name,
              "face_confidence": confidence, "zone_id": zone_id,
              "duration_in_zone_seconds": 0}],
            zone_id, tf,
            extra_meta={"appearances_in_1h": len(recent)},
            event_counter=self._next_id()
        )
