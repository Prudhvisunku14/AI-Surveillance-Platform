"""SQLAlchemy ORM models — spec schemas section 15."""
import uuid
from datetime import datetime
from sqlalchemy import String, Float, Boolean, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class VideoRecord(Base):
    __tablename__ = "videos"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    filename: Mapped[str] = mapped_column(String, unique=True)
    original_name: Mapped[str] = mapped_column(String)
    scenario: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="uploaded")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_frames: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Path to the final annotated video produced by the pipeline
    output_path: Mapped[str | None] = mapped_column(String, nullable=True)
    # Timestamp columns
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    events: Mapped[list["EventRecord"]] = relationship("EventRecord", back_populates="video")


class EventRecord(Base):
    """Canonical event schema — spec section 8."""
    __tablename__ = "events"
    # spec: event_id format EVT_V001_0042
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    video_id: Mapped[str] = mapped_column(String, ForeignKey("videos.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String)        # exact spec catalog
    severity: Mapped[str] = mapped_column(String)          # L1 / L2 / L3
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    frame_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_snapshot_path: Mapped[str | None] = mapped_column(String, nullable=True)
    persons_involved: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    threat_score: Mapped[float] = mapped_column(Float, default=0.0)
    threat_features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    threat_explainability: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    genai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    genai_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by: Mapped[str | None] = mapped_column(String, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    video: Mapped["VideoRecord"] = relationship("VideoRecord", back_populates="events")


class PersonRecord(Base):
    """Person intelligence card — spec section 7."""
    __tablename__ = "persons"
    id: Mapped[str] = mapped_column(String, primary_key=True)  # P001..P005+
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)       # Employee/Visitor/Suspect/Unknown
    risk_level: Mapped[str] = mapped_column(String)     # Low/Medium/High
    access_zones: Mapped[str] = mapped_column(String, default="")
    embedding_path: Mapped[str | None] = mapped_column(String, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    watchlist: Mapped[bool] = mapped_column(Boolean, default=False)
    visit_count_24h: Mapped[int] = mapped_column(Integer, default=0)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    presence_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    confidence_trace: Mapped[list | None] = mapped_column(JSON, nullable=True)


class SensorEventRecord(Base):
    """Sensor event — spec section 4.2 schema."""
    __tablename__ = "sensor_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    event_id: Mapped[str] = mapped_column(String, unique=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    sensor_type: Mapped[str] = mapped_column(String)
    location_id: Mapped[str] = mapped_column(String)
    event: Mapped[str] = mapped_column(String)
    authorized: Mapped[bool] = mapped_column(Boolean, default=True)
    person_id: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    """Immutable audit log — spec: all user actions logged."""
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    resource_type: Mapped[str | None] = mapped_column(String, nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
