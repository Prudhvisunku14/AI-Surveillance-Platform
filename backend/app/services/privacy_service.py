"""Privacy features — spec section 14: face blur, right to erasure, retention deletion."""
import os
import glob
import asyncio
from datetime import datetime, timedelta
from typing import List
from app.core.config import get_settings

settings = get_settings()


async def delete_person_data(person_id: str, db) -> dict:
    """
    Right to Erasure — spec GDPR/PDPA section 14.
    Deletes: embedding file, person DB record, associated events.
    Returns audit trail of what was deleted.
    """
    deleted = []

    # 1. Delete face embedding
    emb_path = os.path.join(settings.embeddings_dir, f"{person_id}.npy")
    if os.path.exists(emb_path):
        os.remove(emb_path)
        deleted.append(f"embedding:{emb_path}")

    # 2. Soft-delete person record in DB
    from app.models.sql_models import PersonRecord
    from sqlalchemy import select, update
    result = await db.execute(select(PersonRecord).where(PersonRecord.id == person_id))
    person = result.scalar_one_or_none()
    if person:
        await db.delete(person)
        await db.commit()
        deleted.append(f"person_record:{person_id}")

    # 3. Anonymise events referencing this person
    from app.models.sql_models import EventRecord
    import json
    result = await db.execute(
        select(EventRecord).where(EventRecord.persons_involved.contains(person_id))
    )
    events = result.scalars().all()
    for ev in events:
        if ev.persons_involved:
            for p in ev.persons_involved:
                if isinstance(p, dict) and p.get("person_id") == person_id:
                    p["person_id"] = "REDACTED"
                    p["display_name"] = "Redacted Person"
        await db.commit()
        deleted.append(f"event_anonymised:{ev.id}")

    return {"person_id": person_id, "deleted": deleted,
            "timestamp": datetime.utcnow().isoformat()}


async def run_retention_cleanup(db):
    """
    Automatic retention deletion — spec: frame snapshots retained 30 days.
    Deletes frames older than FRAME_RETENTION_DAYS.
    """
    cutoff = datetime.utcnow() - timedelta(days=settings.frame_retention_days)
    frames_dir = settings.frame_evidence_dir
    deleted_count = 0

    if os.path.exists(frames_dir):
        for f in glob.glob(os.path.join(frames_dir, "*.jpg")):
            mtime = datetime.utcfromtimestamp(os.path.getmtime(f))
            if mtime < cutoff:
                os.remove(f)
                deleted_count += 1

    return {"deleted_frames": deleted_count, "cutoff": cutoff.isoformat()}


def apply_face_blur_to_frame(frame, tracks: list, face_service) -> any:
    """
    Face blur privacy mode — spec section 14.
    Blurs unknown persons' faces when FACE_BLUR_MODE=true.
    """
    if not settings.face_blur_mode:
        return frame
    for track in tracks:
        if track.get("category") in ("Unknown", None):
            bbox = track.get("bbox", [])
            if len(bbox) == 4:
                frame = face_service.blur_face(frame, bbox)
    return frame
