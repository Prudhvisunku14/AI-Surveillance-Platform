"""FastAPI application entry point — spec section 11."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.database import init_db
from app.api.v1 import api_router

settings = get_settings()

# Setup logging
os.makedirs("logs", exist_ok=True)
setup_logging(log_level="DEBUG" if settings.app_env == "development" else "INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    os.makedirs(settings.frame_evidence_dir, exist_ok=True)
    os.makedirs(settings.report_output_dir, exist_ok=True)
    os.makedirs(settings.embeddings_dir, exist_ok=True)
    os.makedirs("data/videos", exist_ok=True)
    os.makedirs("ml/models", exist_ok=True)

    # Seed persons registry
    await _seed_persons()

    yield  # App runs here

    # Shutdown: clean up


async def _seed_persons():
    """Seed spec face registry P001-P005 into DB."""
    from app.db.database import AsyncSessionLocal
    from app.models.sql_models import PersonRecord
    from sqlalchemy import select
    from app.services.face_recognition import FACE_REGISTRY

    async with AsyncSessionLocal() as db:
        for pid, info in FACE_REGISTRY.items():
            result = await db.execute(select(PersonRecord).where(PersonRecord.id == pid))
            if not result.scalar_one_or_none():
                person = PersonRecord(
                    id=pid, name=info["name"], category=info["category"],
                    risk_level=info["risk_level"], access_zones=info["access_zones"],
                    watchlist=(info["category"] == "Suspect"),
                )
                db.add(person)
        await db.commit()


app = FastAPI(
    title="SurveillanceIQ — AI Surveillance Intelligence Platform",
    description="End-to-end AI surveillance platform with YOLOv8, ByteTrack, DeepFace, and GenAI.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS — spec: React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    from app.core.logging import get_logger
    log = get_logger()
    log.info(f"→ {request.method} {request.url.path}")
    response = await call_next(request)
    log.info(f"← {response.status_code} {request.url.path}")
    return response


# Static file mounts for frame evidence
if os.path.exists("frames"):
    app.mount("/frames", StaticFiles(directory="frames"), name="frames")

# Include all routes
app.include_router(api_router)


@app.get("/")
async def root():
    return {"name": "SurveillanceIQ Platform", "version": "1.0.0",
            "docs": "/docs", "health": "/api/v1/health"}
