"""Generate synthetic sensor events — spec section 4.2.
Produces normal and anomalous sequences, time-aligned with video scenarios."""
import json
import os
import random
from datetime import datetime, timezone, timedelta

random.seed(42)
OUTPUT_DIR = "data/sensor_events"
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_TIME = datetime(2026, 5, 28, 9, 0, 0, tzinfo=timezone.utc)


def ts(offset_s: float) -> str:
    return (BASE_TIME + timedelta(seconds=offset_s)).isoformat()


def make_event(event_id, offset_s, sensor_type, location_id, event, authorized=True,
               person_id=None, confidence=0.97, anomaly_flag=False):
    return {
        "event_id": event_id,
        "timestamp": ts(offset_s),
        "sensor_type": sensor_type,
        "location_id": location_id,
        "event": event,
        "authorized": authorized,
        "person_id": person_id,
        "confidence": confidence,
        "anomaly_flag": anomaly_flag,
    }


events = []

# ── Normal sequences ─────────────────────────────────────────
# P001 Alice — authorized entry
events.append(make_event("EVT_0001", 5.0, "biometric", "DOOR_A1", "face_scan_success",
                           True, "P001", 0.97))
events.append(make_event("EVT_0002", 5.2, "door_access", "DOOR_A1", "door_open",
                           True, "P001", 0.97))

# P002 Bob — authorized entry
events.append(make_event("EVT_0003", 12.0, "biometric", "DOOR_A1", "face_scan_success",
                           True, "P002", 0.94))
events.append(make_event("EVT_0004", 12.2, "door_access", "DOOR_A1", "door_open",
                           True, "P002", 0.94))

# Motion in lobby (normal)
for i, t in enumerate([8, 15, 22, 35, 50], start=5):
    events.append(make_event(f"EVT_{i:04d}", t, "motion", "LOBBY_Z01", "motion_detected",
                               True, None, round(random.uniform(0.7, 0.95), 2)))

# ── Anomaly 1: Door opened — no video person detected ────────
events.append(make_event("EVT_0010", 25.0, "door_access", "DOOR_B2", "door_open",
                           True, "P001", 0.95, anomaly_flag=True))
# No corresponding video detection (video shows empty corridor)

# ── Anomaly 2: Tailgating — 2 persons on single badge ───────
events.append(make_event("EVT_0011", 45.0, "biometric", "DOOR_A1", "face_scan_success",
                           True, "P001", 0.96))
events.append(make_event("EVT_0012", 45.2, "door_access", "DOOR_A1", "door_tailgate",
                           True, "P001", 0.96, anomaly_flag=True))
# Video shows 2 persons entering simultaneously

# ── Anomaly 3: Identity mismatch ─────────────────────────────
events.append(make_event("EVT_0013", 55.0, "biometric", "DOOR_C3", "face_scan_success",
                           True, "P001", 0.95))
# Video face recognition matches P004 (Dave Rostov — suspect)
events.append(make_event("EVT_0014", 55.1, "camera_trigger", "CAM_C3", "motion_detected",
                           True, "P004", 0.88, anomaly_flag=True))

# ── Anomaly 4: Motion in closed zone ─────────────────────────
events.append(make_event("EVT_0015", 70.0, "motion", "SERVER_ROOM_Z02", "motion_detected",
                           False, None, 0.91, anomaly_flag=True))
# No access log for server room at this time

# ── Anomaly 5: Repeated failed biometrics then open ──────────
events.append(make_event("EVT_0016", 80.0, "biometric", "DOOR_D4", "face_scan_fail",
                           False, None, 0.31))
events.append(make_event("EVT_0017", 82.0, "biometric", "DOOR_D4", "face_scan_fail",
                           False, None, 0.28))
events.append(make_event("EVT_0018", 84.0, "biometric", "DOOR_D4", "face_scan_fail",
                           False, None, 0.25))
events.append(make_event("EVT_0019", 86.0, "door_access", "DOOR_D4", "door_open",
                           True, "P005", 0.55, anomaly_flag=True))
# Forced/piggyback entry after repeated failures

# ── Anomaly 6: P003 Carol in restricted zone (sensor) ────────
events.append(make_event("EVT_0020", 90.0, "camera_trigger", "CAM_Z02", "motion_detected",
                           False, "P003", 0.85, anomaly_flag=True))

# Save
output_path = os.path.join(OUTPUT_DIR, "sensor_events.json")
with open(output_path, "w") as f:
    json.dump(events, f, indent=2)

normal = sum(1 for e in events if not e["anomaly_flag"])
anomalous = sum(1 for e in events if e["anomaly_flag"])
print(f"✅ Generated {len(events)} sensor events → {output_path}")
print(f"   Normal: {normal} | Anomalous: {anomalous}")
print(f"   Anomaly types:")
print(f"   - Door open with no video corroboration")
print(f"   - Tailgating (2 persons on 1 badge)")
print(f"   - Identity mismatch (sensor P001 ≠ video P004)")
print(f"   - Motion in closed zone (no access log)")
print(f"   - Repeated failed biometrics → door open")
print(f"   - Visitor in restricted zone")
