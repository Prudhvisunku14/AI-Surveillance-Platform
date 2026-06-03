'''Application configuration — exact values from specification.'''
from functools import lru_cache
from typing import Optional

# Import BaseSettings from the correct package
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    app_name: str = "SurveillanceIQ Platform"
    app_env: str = "development"
    debug: bool = True

    # Security
    secret_key: str = "surveillance-platform-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Database
    database_url: str = "sqlite+aiosqlite:///./surveillance.db"
    mongo_uri: str = "mongodb://surv_user:surv_pass@mongo:27017/surveillance"
    redis_url: str = "redis://redis:6379/0"

    # Celery
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # YOLO
    yolo_model_path: str = "ml/models/yolov8n.pt"
    yolo_confidence: float = 0.45

    # Face Recognition
    face_model_backend: str = "Facenet512"
    face_similarity_threshold: float = 0.82
    face_tentative_threshold: float = 0.60
    embeddings_dir: str = "ml/embeddings/"

    # GenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    genai_enabled: bool = True

    # Storage
    report_output_dir: str = "reports/"
    frame_evidence_dir: str = "frames/"
    frame_retention_days: int = 30

    # Loitering
    loitering_warning_seconds: int = 120
    loitering_critical_seconds: int = 300

    # Tracking
    track_reidentify_after_frames: int = 30

    # Abandoned Object
    abandoned_object_seconds: int = 60

    # Repeated Reappearance
    repeated_reappearance_count: int = 3
    repeated_reappearance_window_hours: int = 1

    # Privacy
    face_blur_mode: bool = False
    enable_right_to_erasure: bool = True

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()