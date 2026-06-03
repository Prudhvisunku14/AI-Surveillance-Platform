"""Generate synthetic surveillance videos — spec section 4.1.
Creates 3 MP4 videos with JSON annotation sidecars."""
import cv2
import json
import os
import numpy as np
import random
from dataclasses import dataclass, field
from typing import List, Tuple

random.seed(42)
np.random.seed(42)

OUTPUT_DIR = "data/videos"
ANNOTATIONS_DIR = "data/annotations"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ANNOTATIONS_DIR, exist_ok=True)

W, H = 800, 600
FPS = 25


@dataclass
class SimPerson:
    person_id: str
    color: Tuple[int, int, int]
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    width: int = 50
    height: int = 120


def draw_person(frame, p: SimPerson, label: str = ""):
    x, y = int(p.x), int(p.y)
    cv2.rectangle(frame, (x - p.width//2, y - p.height//2),
                  (x + p.width//2, y + p.height//2), p.color, -1)
    # Head
    cv2.circle(frame, (x, y - p.height//2 - 15), 15, p.color, -1)
    if label:
        cv2.putText(frame, label, (x - 20, y - p.height//2 - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)


def make_video(filename: str, duration_s: int, fps: int,
               scenario_fn, scenario_name: str, video_id: str,
               expected_events: List[dict]):
    path = os.path.join(OUTPUT_DIR, filename)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (W, H))

    total_frames = duration_s * fps
    for frame_idx in range(total_frames):
        t = frame_idx / fps
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        # Background
        cv2.rectangle(frame, (0, 0), (W, H), (30, 35, 45), -1)
        # Floor tiles
        for gx in range(0, W, 100):
            cv2.line(frame, (gx, 0), (gx, H), (40, 45, 55), 1)
        for gy in range(0, H, 100):
            cv2.line(frame, (0, gy), (W, gy), (40, 45, 55), 1)
        # Zone overlays
        cv2.rectangle(frame, (0, 0), (400, 300), (50, 20, 20), -1)
        cv2.putText(frame, "RESTRICTED ZONE Z02", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 50, 50), 1)
        cv2.rectangle(frame, (50, 400), (750, 580), (20, 50, 20), -1)
        cv2.putText(frame, "LOBBY Z01", (55, 420),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (50, 100, 50), 1)

        # Run scenario
        scenario_fn(frame, frame_idx, t, fps)

        # Timestamp
        cv2.putText(frame, f"Camera: {video_id} | t={t:.1f}s | Frame:{frame_idx}",
                    (5, H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        writer.write(frame)

    writer.release()

    # JSON annotation sidecar — spec format section 4.1
    annotation = {
        "video_id": video_id,
        "source": "synthetic_opencv",
        "duration_seconds": duration_s,
        "fps": fps,
        "scenario": scenario_name,
        "expected_events": expected_events,
    }
    ann_path = os.path.join(ANNOTATIONS_DIR, f"{video_id}.json")
    with open(ann_path, "w") as f:
        json.dump(annotation, f, indent=2)

    file_size = os.path.getsize(path) / (1024 * 1024)
    print(f"  ✅ {filename}: {duration_s}s, {total_frames} frames, {file_size:.1f}MB")
    return path


# ── Scenario 1: Lobby Entry ──────────────────────────────────
persons_v001 = [
    SimPerson("P001", (0, 200, 0), 400.0, 500.0, 2.0, -0.5),
    SimPerson("P002", (0, 180, 0), 100.0, 500.0, 1.5, 0.0),
    SimPerson("UNKNOWN_01", (0, 0, 200), 700.0, 300.0, 0.2, 0.1),
]

def scenario_lobby(frame, frame_idx, t, fps):
    p = persons_v001[0]
    p.x = min(750, max(50, p.x + p.vx))
    p.y = min(570, max(30, p.y + p.vy))
    draw_person(frame, p, "P001-Alice")

    p2 = persons_v001[1]
    if t < 60:
        p2.x = min(750, max(50, p2.x + p2.vx))
        draw_person(frame, p2, "P002-Bob")

    # UNKNOWN loiters from t=30
    p3 = persons_v001[2]
    if t >= 30:
        draw_person(frame, p3, "UNKNOWN")


# ── Scenario 2: Corridor / Loitering ────────────────────────
persons_v002 = [
    SimPerson("P003", (0, 165, 255), 200.0, 200.0, 0.1, 0.05),
    SimPerson("P004", (0, 0, 255), 300.0, 150.0, 0.05, 0.02),
]

def scenario_corridor(frame, frame_idx, t, fps):
    p = persons_v002[0]  # Carol — loiters in restricted zone
    p.x += random.uniform(-0.5, 0.5)
    p.y += random.uniform(-0.5, 0.5)
    draw_person(frame, p, "P003-Carol")

    p2 = persons_v002[1]  # Dave — suspect
    if t >= 20:
        p2.x = min(380, max(10, p2.x + p2.vx))
        draw_person(frame, p2, "P004-SUSPECT")

    cv2.putText(frame, f"Zone Z02 occupancy: 2", (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 100, 100), 1)


# ── Scenario 3: Open Area (sudden movement, crowd) ──────────
persons_v003 = [
    SimPerson("P001", (0, 200, 0), 100.0, 450.0, 1.0, 0.0),
    SimPerson("P002", (0, 180, 0), 200.0, 480.0, 1.2, 0.0),
    SimPerson("P003", (0, 165, 255), 300.0, 460.0, 0.8, 0.0),
    SimPerson("ERRATIC", (0, 0, 200), 400.0, 500.0, 0.0, 0.0),
]

def scenario_open(frame, frame_idx, t, fps):
    for i, p in enumerate(persons_v003[:3]):
        p.x = min(750, max(50, p.x + p.vx))
        draw_person(frame, p, f"P{i+1:03d}")

    # Sudden movement at t=20
    p_e = persons_v003[3]
    if 20 <= t <= 25:
        p_e.x = min(750, max(50, p_e.x + 15))  # High velocity
        p_e.y = min(570, max(30, p_e.y - 8))
    else:
        p_e.x = min(750, max(50, p_e.x + 0.5))
    draw_person(frame, p_e, "ERRATIC")
    cv2.putText(frame, f"Crowd: {4}", (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 100, 100), 1)


if __name__ == "__main__":
    print("🎬 Generating synthetic surveillance videos...")
    print("=" * 50)

    make_video("V001_lobby_entry.mp4", 90, FPS, scenario_lobby,
               "lobby_entry", "V001", [
                   {"type": "identity_verified", "timestamp_sec": 3.0, "person_id": "P001"},
                   {"type": "loitering_warning", "timestamp_sec": 30.0, "person_id": "UNKNOWN_01"},
                   {"type": "person_exited", "timestamp_sec": 60.0, "person_id": "P002"},
               ])

    make_video("V002_corridor_loitering.mp4", 120, FPS, scenario_corridor,
               "corridor_loitering", "V002", [
                   {"type": "zone_violation", "timestamp_sec": 2.0, "person_id": "P003"},
                   {"type": "loitering_critical", "timestamp_sec": 60.0, "person_id": "P003"},
                   {"type": "suspect_detected", "timestamp_sec": 20.0, "person_id": "P004"},
               ])

    make_video("V003_open_area.mp4", 60, FPS, scenario_open,
               "open_area", "V003", [
                   {"type": "crowd_alert", "timestamp_sec": 5.0, "person_id": "multiple"},
                   {"type": "sudden_movement", "timestamp_sec": 20.0, "person_id": "ERRATIC"},
               ])

    print("=" * 50)
    print("✅ All 3 videos generated in data/videos/")
    print("✅ Annotation sidecars in data/annotations/")
