#!/usr/bin/env python3
"""
Local YOLOv8 Person Detector Pipeline.
Detects only persons (class 0) at confidence 0.45,
renders telemetry overlays and saves output_detected.mp4.
Run from project root: python run_person_detector.py
"""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
# Add backend to sys.path so "app.*" imports work
root_dir = os.path.abspath(os.path.dirname(__file__))
backend_dir = os.path.join(root_dir, "backend")
sys.path.insert(0, root_dir)
sys.path.insert(0, backend_dir)

try:
    import torch
    torch.backends.mkldnn.enabled = False
except ImportError:
    pass

import cv2
import argparse
from app.services.tracker import ByteTracker

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    print("⚠️  ultralytics not installed — using mock detections")


def main():
    parser = argparse.ArgumentParser(description="Local YOLOv8 Person Detector Pipeline")
    parser.add_argument("--input", type=str, default="data/videos/V001_lobby_entry.mp4",
                        help="Path to input video file")
    parser.add_argument("--output", type=str, default="output_detected.mp4",
                        help="Path to output video file")
    parser.add_argument("--conf", type=float, default=0.45,
                        help="Detection confidence threshold (spec: 0.45)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ Input video not found: '{args.input}'")
        print("💡 Run: python ml/generate_synthetic_videos.py")
        return

    print(f"🎬 Loading: {args.input}")
    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        print(f"❌ Cannot open video: {args.input}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 100
    print(f"📐 {width}x{height} @ {fps:.1f}fps | {total_frames} frames")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(args.output, fourcc, fps, (width, height))
    if not out.isOpened():
        out = cv2.VideoWriter(args.output.replace(".mp4", ".avi"),
                              cv2.VideoWriter_fourcc(*"XVID"), fps, (width, height))

    model = YOLO("yolov8n.pt") if HAS_YOLO else None
    tracker = ByteTracker()

    BOX_COLOR = (0, 255, 0)
    TEXT_COLOR = (255, 255, 255)

    print("\n🧠 Processing frames...")
    frame_iter = range(total_frames)
    if HAS_TQDM:
        frame_iter = tqdm(frame_iter, desc="Rendering", unit="fr")

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        # YOLOv8 detection (persons only, conf=0.45)
        detections = []
        if model:
            results = model(frame, conf=args.conf, classes=[0], verbose=False)
            if results:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                    conf_score = float(box.conf[0])
                    detections.append({"bbox": [x1, y1, x2, y2], "confidence": conf_score})
        else:
            # Mock detection for testing without ultralytics
            h, w = frame.shape[:2]
            detections = [{"bbox": [int(w * 0.2), int(h * 0.1), int(w * 0.4), int(h * 0.9)],
                           "confidence": 0.87}]

        # ByteTrack tracking
        active_tracks = tracker.update(detections)
        person_count = len(active_tracks)

        # Draw bounding boxes + track IDs
        for tid, track in active_tracks.items():
            x1, y1, x2, y2 = track.bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, 2)
            label = f"ID:{tid}"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (x1, y1 - 20), (x1 + lw + 8, y1), BOX_COLOR, -1)
            cv2.putText(frame, label, (x1 + 4, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

        # Telemetry overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (300, 70), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        cv2.putText(frame, "SurveillanceIQ", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, BOX_COLOR, 1)
        cv2.putText(frame, f"Persons: {person_count} | Frame: {frame_idx}",
                    (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_COLOR, 1)

        out.write(frame)
        if HAS_TQDM:
            frame_iter.update(1)

    cap.release()
    out.release()
    print(f"\n✅ Done! Saved: {os.path.abspath(args.output)}")
    print(f"   Processed {frame_idx} frames, final track count: {len(active_tracks)}")


if __name__ == "__main__":
    main()
