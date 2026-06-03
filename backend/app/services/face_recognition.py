"""Face recognition — DeepFace + FaceNet512 + FAISS.
Spec: >=0.82 positive, 0.60-0.82 tentative, <0.60 unknown."""
import os
import json
import time
import numpy as np
from typing import Optional, Tuple, Dict, List
from app.core.config import get_settings

settings = get_settings()

try:
    from deepface import DeepFace
    import faiss
    _DEEPFACE_AVAILABLE = True
except ImportError:
    _DEEPFACE_AVAILABLE = False

# Spec face identity database — P001-P005
FACE_REGISTRY = {
    "P001": {"name": "Alice Mercer", "category": "Employee", "risk_level": "Low",
             "access_zones": "Lobby, Lab A, Server Room"},
    "P002": {"name": "Bob Henley", "category": "Employee", "risk_level": "Low",
             "access_zones": "Lobby, Lab A"},
    "P003": {"name": "Carol Zhang", "category": "Visitor", "risk_level": "Medium",
             "access_zones": "Lobby only"},
    "P004": {"name": "Dave Rostov", "category": "Suspect", "risk_level": "High",
             "access_zones": "NONE — flagged"},
    "P005": {"name": "Unknown", "category": "Unknown", "risk_level": "High",
             "access_zones": "NONE"},
}


class FaceRecognitionService:
    """DeepFace FaceNet512 + FAISS — spec section 7."""

    POSITIVE_THRESHOLD = 0.82    # spec exact
    TENTATIVE_THRESHOLD = 0.60   # spec exact
    EMBEDDING_DIM = 512          # FaceNet512

    def __init__(self):
        self.embeddings_dir = settings.embeddings_dir
        os.makedirs(self.embeddings_dir, exist_ok=True)
        self.index = None
        self.person_ids: List[str] = []
        self._load_index()

    def _load_index(self):
        """Load FAISS index from stored embeddings."""
        embeddings, ids = [], []
        for person_id in FACE_REGISTRY:
            emb_path = os.path.join(self.embeddings_dir, f"{person_id}.npy")
            if os.path.exists(emb_path):
                emb = np.load(emb_path).astype(np.float32)
                if emb.shape[0] == self.EMBEDDING_DIM:
                    embeddings.append(emb)
                    ids.append(person_id)
        if embeddings:
            emb_matrix = np.stack(embeddings)
            faiss.normalize_L2(emb_matrix)
            self.index = faiss.IndexFlatIP(self.EMBEDDING_DIM)
            self.index.add(emb_matrix)
            self.person_ids = ids

    def get_embedding(self, face_img: np.ndarray) -> Optional[np.ndarray]:
        """Extract 512-d FaceNet512 embedding."""
        if not _DEEPFACE_AVAILABLE:
            return np.random.randn(self.EMBEDDING_DIM).astype(np.float32)
        try:
            result = DeepFace.represent(
                img_path=face_img,
                model_name="Facenet512",
                enforce_detection=False,
                detector_backend="skip",
            )
            if result:
                return np.array(result[0]["embedding"], dtype=np.float32)
        except Exception:
            pass
        return None

    def identify(self, face_img: np.ndarray, attempt: int = 1) -> dict:
        """
        Classify identity per spec thresholds.
        Returns: {person_id, display_name, category, confidence, classification}
        """
        emb = self.get_embedding(face_img)
        if emb is None:
            return self._unknown_result()

        if self.index is None or len(self.person_ids) == 0:
            return self._unknown_result()

        query = emb.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query)
        D, I = self.index.search(query, 1)
        similarity = float(D[0][0])  # cosine similarity (0-1 after L2 norm)
        idx = int(I[0][0])

        if similarity >= self.POSITIVE_THRESHOLD:
            pid = self.person_ids[idx]
            info = FACE_REGISTRY[pid]
            return {
                "person_id": pid,
                "display_name": info["name"],
                "category": info["category"],
                "risk_level": info["risk_level"],
                "confidence": similarity,
                "classification": "positive",
                "is_known": True,
            }
        elif similarity >= self.TENTATIVE_THRESHOLD:
            pid = self.person_ids[idx]
            info = FACE_REGISTRY[pid]
            return {
                "person_id": f"TENTATIVE_{pid}",
                "display_name": f"Possibly {info['name']}",
                "category": info["category"],
                "risk_level": info["risk_level"],
                "confidence": similarity,
                "classification": "tentative",
                "is_known": False,
            }
        else:
            uid = f"UNKNOWN_{int(time.time()) % 10000:04d}"
            return {
                "person_id": uid,
                "display_name": "Unknown Person",
                "category": "Unknown",
                "risk_level": "High",
                "confidence": similarity,
                "classification": "unknown",
                "is_known": False,
            }

    def register_face(self, person_id: str, face_img: np.ndarray) -> bool:
        """Register face — spec /api/v1/faces/register."""
        emb = self.get_embedding(face_img)
        if emb is None:
            return False
        os.makedirs(self.embeddings_dir, exist_ok=True)
        np.save(os.path.join(self.embeddings_dir, f"{person_id}.npy"), emb)
        self._load_index()
        return True

    def delete_person(self, person_id: str) -> bool:
        """GDPR right to erasure — spec section 14."""
        emb_path = os.path.join(self.embeddings_dir, f"{person_id}.npy")
        if os.path.exists(emb_path):
            os.remove(emb_path)
            self._load_index()
            return True
        return False

    def blur_face(self, frame: np.ndarray, bbox: List[int]) -> np.ndarray:
        """Privacy feature: face blur for unknown persons — spec section 14."""
        x1, y1, x2, y2 = bbox
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
        if x2 > x1 and y2 > y1:
            roi = frame[y1:y2, x1:x2]
            roi = cv2.GaussianBlur(roi, (99, 99), 30)
            frame[y1:y2, x1:x2] = roi
        return frame

    def _unknown_result(self) -> dict:
        uid = f"UNKNOWN_{int(time.time()) % 10000:04d}"
        return {"person_id": uid, "display_name": "Unknown Person", "category": "Unknown",
                "risk_level": "High", "confidence": 0.0, "classification": "unknown",
                "is_known": False}


# Import cv2 for blur — lazy to avoid import error at module level
try:
    import cv2
except ImportError:
    pass

# Singleton
_face_service: Optional[FaceRecognitionService] = None


def get_face_service() -> FaceRecognitionService:
    global _face_service
    if _face_service is None:
        _face_service = FaceRecognitionService()
    return _face_service
