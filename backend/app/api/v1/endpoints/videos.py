"""Video endpoints — exact spec routes section 11."""
import os
import uuid
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.sql_models import VideoRecord
from app.schemas.schemas import VideoUploadResponse, VideoStatus
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/videos", tags=["videos"])
DATA_DIR = "data/videos"


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    scenario: str = Form(default=""),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    os.makedirs(DATA_DIR, exist_ok=True)
    video_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] or ".mp4"
    filename = f"{video_id}{ext}"
    file_path = os.path.join(DATA_DIR, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    record = VideoRecord(
        id=video_id,
        filename=filename,
        original_name=file.filename,
        scenario=scenario,
        status="uploaded",
    )
    db.add(record)
    await db.commit()

    return VideoUploadResponse(
        id=video_id, filename=filename,
        original_name=file.filename, status="uploaded",
        uploaded_at=record.uploaded_at,
    )


@router.post("/{video_id}/process")
async def process_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(VideoRecord).where(VideoRecord.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status == "processing":
        raise HTTPException(status_code=409, detail="Already processing")

    file_path = os.path.join(DATA_DIR, video.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    # Try Celery first, fallback to background task
    try:
        from app.tasks.video_tasks import process_video as celery_task
        task = celery_task.delay(video_id, file_path)
        return {"task_id": task.id, "status": "queued", "video_id": video_id}
    except Exception:
        # Fallback: run in background
        background_tasks.add_task(_process_in_background, video_id, file_path)
        return {"task_id": "bg_" + video_id, "status": "queued", "video_id": video_id}


async def _process_in_background(video_id: str, file_path: str):
    import cv2
    from app.db.database import AsyncSessionLocal
    from app.models.sql_models import VideoRecord, EventRecord
    from app.services.vision_pipeline import VisionPipeline
    from app.services.genai_service import generate_incident_summary
    from datetime import timezone

    async with AsyncSessionLocal() as db:
        r = await db.execute(select(VideoRecord).where(VideoRecord.id == video_id))
        video = r.scalar_one_or_none()
        if not video:
            return
        video.status = "processing"
        await db.commit()

        cap = cv2.VideoCapture(file_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video.fps = fps
        video.total_frames = total
        video.duration_seconds = total / fps if fps > 0 else 0
        await db.commit()

        pipeline = VisionPipeline(video_id=video_id)
        frame_skip = max(1, int(fps / 5))
        idx = 0
        processed = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            idx += 1
            if idx % frame_skip != 0:
                continue
            _, events = pipeline.process_frame(frame, idx)
            processed += 1
            for ev in events:
                if ev.get("severity") in ("L2", "L2+", "L3"):
                    genai_data = await generate_incident_summary(ev)
                    ev["genai_data"] = genai_data
                    db_ev = EventRecord(
                        id=ev.get("event_id", str(idx)),
                        video_id=video_id,
                        event_type=ev["event_type"],
                        severity=ev["severity"],
                        timestamp=datetime.now(timezone.utc),
                        frame_index=ev.get("frame_index"),
                        frame_snapshot_path=ev.get("frame_snapshot_path"),
                        persons_involved=ev.get("persons_involved"),
                        threat_score=ev.get("threat_score", 0.0),
                        threat_features=ev.get("threat_features"),
                        threat_explainability=ev.get("threat_explainability"),
                        genai_summary=genai_data.get("incident_summary") if genai_data else None,
                        genai_data=genai_data,
                        zone_id=ev.get("zone_id"),
                        metadata_extra=ev.get("metadata_extra"),
                    )
                    try:
                        db.add(db_ev)
                        await db.commit()
                    except Exception:
                        await db.rollback()
                    try:
                        from app.db.redis_client import publish_event
                        await publish_event("alerts", ev)
                    except Exception:
                        pass
            if total > 0:
                video.progress = min(99, int(processed * frame_skip * 100 / total))
                if processed % 30 == 0:
                    await db.commit()
        cap.release()
        video.status = "completed"
        video.progress = 100
        video.processed_at = datetime.utcnow()
        await db.commit()


@router.get("/{video_id}/status", response_model=VideoStatus)
async def get_video_status(
    video_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(VideoRecord).where(VideoRecord.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return VideoStatus(
        id=video.id, status=video.status, progress=video.progress,
        fps=video.fps, total_frames=video.total_frames,
        duration_seconds=video.duration_seconds,
        processed_at=video.processed_at, error_message=video.error_message,
    )


@router.get("")
async def list_videos(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(VideoRecord).order_by(VideoRecord.uploaded_at.desc()))
    videos = result.scalars().all()
    return [{"id": v.id, "original_name": v.original_name, "scenario": v.scenario,
             "status": v.status, "progress": v.progress, "uploaded_at": v.uploaded_at,
             "duration_seconds": v.duration_seconds} for v in videos]
