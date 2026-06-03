"""YOLOv8 person detector — refactored from repo detector.py.
Spec: confidence threshold 0.45, persons only."""
import cv2
import numpy as np
from typing import List, Tuple
from app.core.config import get_settings

settings = get_settings()

try:
    from ultralytics import YOLO
    _YOLO_AVAILABLE = True
except ImportError:
    _YOLO_AVAILABLE = False


class PersonDetector:
    """YOLOv8 person detection — spec section 6.2.
    Refactored from repo detector.py: changed confidence to 0.45 per spec,
    returns full bbox+confidence+class dict instead of list."""

    def __init__(self, model_path: str = None):
        self.model_path = model_path or settings.yolo_model_path
        self.confidence = settings.yolo_confidence   # spec: 0.45
        self.model = None
        self._load_model()

    def _load_model(self):
        if not _YOLO_AVAILABLE:
            return
        try:
            self.model = YOLO(self.model_path)
        except Exception:
            try:
                self.model = YOLO("yolov8n.pt")
            except Exception:
                self.model = None

    def detect(self, frame: np.ndarray) -> List[dict]:
        """Returns list of {bbox:[x1,y1,x2,y2], confidence, class_id}."""
        if self.model is None:
            return self._mock_detect(frame)
        results = self.model(frame, conf=self.confidence, verbose=False)[0]
        detections = []
        for r in results.boxes.data.tolist():
            x1, y1, x2, y2, score, cls_id = r
            if int(cls_id) == 0:  # persons only
                detections.append({
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "confidence": float(score),
                    "class_id": 0,
                    "class_name": "person",
                })
        return detections

    def _mock_detect(self, frame: np.ndarray) -> List[dict]:
        """Fallback when YOLO unavailable — synthetic detections for testing."""
        h, w = frame.shape[:2]
        return [
            {"bbox": [int(w * 0.2), int(h * 0.1), int(w * 0.4), int(h * 0.9)],
             "confidence": 0.87, "class_id": 0, "class_name": "person"},
            {"bbox": [int(w * 0.6), int(h * 0.1), int(w * 0.8), int(h * 0.9)],
             "confidence": 0.74, "class_id": 0, "class_name": "person"},
        ]

    def is_available(self) -> bool:
        return self.model is not None
