"""Celery video processing task — full pipeline orchestration."""
import os
import cv2
import asyncio
from datetime import datetime, timezone
from app.core.celery_app import celery_app


@celery_app.task(bind=True, name="app.tasks.video_tasks.process_video", queue="video")
def process_video(self, video_id: str, file_path: str):
    """
    Full CV pipeline: frame extraction → detection → tracking → face recog → events → DB.
    Updates video status/progress in DB.
    """
    from app.db.database import AsyncSessionLocal
    from app.models.sql_models import VideoRecord, EventRecord
    from app.services.vision_pipeline import VisionPipeline
    from app.services.genai_service import generate_incident_summary
    import asyncio as aio

    async def _run():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            result = await db.execute(select(VideoRecord).where(VideoRecord.id == video_id))
            video = result.scalar_one_or_none()
            if not video:
                return

            video.status = "processing"
            await db.commit()

            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                video.status = "failed"
                video.error_message = f"Cannot open video: {file_path}"
                await db.commit()
                return

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            duration = total_frames / fps if fps > 0 else 0

            video.fps = fps
            video.total_frames = total_frames
            video.duration_seconds = duration
            await db.commit()

            # Process at 5 FPS (spec: configurable target FPS)
            frame_skip = max(1, int(fps / 5))
            pipeline = VisionPipeline(video_id=video_id)
            processed_frames = 0
            # Prepare VideoWriter for the annotated output video
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "tracked_video_final.mp4")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_idx += 1
                if frame_idx % frame_skip != 0:
                    continue

                annotated_frame, new_events = pipeline.process_frame(frame, frame_idx)
                processed_frames += 1

                # Write the annotated frame to the output video
                if writer is not None:
                    writer.write(annotated_frame)

                # Store L2+ events in DB immediately
                for ev in new_events:
                    if ev.get("severity") in ("L2", "L2+", "L3"):
                        # Generate GenAI summary
                        genai_data = await generate_incident_summary(ev)
                        ev["genai_data"] = genai_data
                        ev["genai_summary"] = genai_data.get("incident_summary") if genai_data else None

                        db_event = EventRecord(
                            id=ev.get("event_id", str(datetime.utcnow().timestamp())),
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
                            genai_summary=ev.get("genai_summary"),
                            genai_data=ev.get("genai_data"),
                            zone_id=ev.get("zone_id"),
                            metadata_extra=ev.get("metadata_extra"),
                        )
                        try:
                            db.add(db_event)
                            await db.commit()
                        except Exception:
                            await db.rollback()

                        # Publish to Redis for WebSocket
                        try:
                            from app.db.redis_client import publish_event
                            await publish_event("alerts", {**ev, "genai_data": genai_data})
                        except Exception:
                            pass

                # Update progress
                if total_frames > 0:
                    progress = min(99, int(processed_frames * frame_skip * 100 / total_frames))
                    self.update_state(state="PROGRESS", meta={"progress": progress})
                    video.progress = progress
                    if processed_frames % 50 == 0:
                        await db.commit()

            cap.release()
            # Release the video writer
            if writer is not None:
                writer.release()

            # Persist the output video path in the VideoRecord
            video.output_path = output_path
            await db.commit()

            # Mark complete
            video.status = "completed"
            video.progress = 100
            video.processed_at = datetime.utcnow()
            from sqlalchemy import func
            r = await db.execute(
                select(func.count(EventRecord.id)).where(EventRecord.video_id == video_id)
            )
            video.event_count = r.scalar() or 0
            await db.commit()

    aio.run(_run())
    return {"status": "completed", "video_id": video_id}
