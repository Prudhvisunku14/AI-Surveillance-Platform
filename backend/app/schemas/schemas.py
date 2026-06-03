"""Pydantic schemas — exact spec API contracts, no changes."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ── Auth ─────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    username: str
    role: str
    full_name: str


# ── Videos ───────────────────────────────────────────────────
class VideoUploadResponse(BaseModel):
    id: str
    filename: str
    original_name: str
    status: str
    uploaded_at: datetime


class VideoStatus(BaseModel):
    id: str
    status: str
    progress: int
    fps: Optional[float]
    total_frames: Optional[int]
    duration_seconds: Optional[float]
    processed_at: Optional[datetime]
    error_message: Optional[str]


# ── Persons Involved (canonical event sub-schema) ─────────────
class PersonInvolved(BaseModel):
    track_id: int
    person_id: str
    display_name: str
    face_confidence: float
    zone_id: Optional[str]
    duration_in_zone_seconds: Optional[float]


# ── Events — canonical spec schema section 8 ─────────────────
class EventSchema(BaseModel):
    event_id: str
    video_id: Optional[str]
    event_type: str       # exact spec catalog values
    severity: str         # L1 / L2 / L3
    timestamp: datetime
    frame_index: Optional[int]
    frame_snapshot_path: Optional[str]
    persons_involved: Optional[List[PersonInvolved]]
    threat_score: float
    threat_features: Optional[Dict[str, Any]]
    threat_explainability: Optional[Dict[str, Any]]
    genai_summary: Optional[str]
    genai_data: Optional[Dict[str, Any]]
    acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    zone_id: Optional[str]


class EventListResponse(BaseModel):
    items: List[EventSchema]
    total: int
    page: int
    page_size: int


class AcknowledgeRequest(BaseModel):
    analyst_name: str


class AcknowledgeResponse(BaseModel):
    success: bool
    acknowledged_by: str
    acknowledged_at: datetime


# ── Persons ───────────────────────────────────────────────────
class PersonCard(BaseModel):
    id: str
    name: str
    category: str
    risk_level: str
    access_zones: str
    watchlist: bool
    visit_count_24h: int
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    presence_duration_seconds: int
    confidence_trace: Optional[List[float]]
    registered_at: datetime


# ── Face Registration ─────────────────────────────────────────
class FaceRegisterResponse(BaseModel):
    success: bool
    person_id: str
    message: str


# ── Sensor Ingest ─────────────────────────────────────────────
class SensorEventIn(BaseModel):
    event_id: str
    timestamp: datetime
    sensor_type: str
    location_id: str
    event: str
    authorized: bool = True
    person_id: Optional[str] = None
    confidence: float = 1.0
    anomaly_flag: bool = False


class SensorIngestResponse(BaseModel):
    ingested: int
    anomalies_detected: int


# ── Health ─────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    yolo: str
    genai: str
    version: str = "1.0.0"


# ── GenAI Output — exact spec section 10 ──────────────────────
class GenAIOutput(BaseModel):
    incident_summary: str
    classification_reasoning: str
    recommended_action: str
    confidence_note: str
