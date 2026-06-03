"""Person endpoints + face registration — spec section 11."""
import os
import shutil
import uuid
import numpy as np
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.sql_models import PersonRecord, AuditLog
from app.services.face_recognition import FACE_REGISTRY, get_face_service
from app.services.privacy_service import delete_person_data
from app.schemas.schemas import FaceRegisterResponse

router = APIRouter(tags=["persons"])


@router.get("/persons")
async def list_persons(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tracked persons — spec section 11."""
    result = await db.execute(select(PersonRecord))
    persons = result.scalars().all()
    return [_person_to_dict(p) for p in persons]


@router.get("/persons/{person_id}/card")
async def get_person_card(
    person_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full person intelligence card — spec section 11."""
    result = await db.execute(select(PersonRecord).where(PersonRecord.id == person_id))
    person = result.scalar_one_or_none()
    if not person:
        # Try registry
        if person_id in FACE_REGISTRY:
            info = FACE_REGISTRY[person_id]
            return {"id": person_id, **info, "visit_count_24h": 0,
                    "confidence_trace": [], "presence_duration_seconds": 0}
        raise HTTPException(status_code=404, detail="Person not found")
    return _person_to_dict(person)


@router.post("/faces/register", response_model=FaceRegisterResponse)
async def register_face(
    person_id: str = Form(...),
    name: str = Form(...),
    category: str = Form(...),
    risk_level: str = Form(...),
    access_zones: str = Form(default=""),
    face_image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register face in identity database — spec section 11."""
    if current_user["role"] not in ("analyst", "admin"):
        raise HTTPException(status_code=403, detail="Analyst or Admin required")

    # Save temp image
    tmp = f"/tmp/{uuid.uuid4()}.jpg"
    with open(tmp, "wb") as f:
        shutil.copyfileobj(face_image.file, f)

    try:
        import cv2
        img = cv2.imread(tmp)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image")

        face_svc = get_face_service()
        ok = face_svc.register_face(person_id, img)
        if not ok:
            raise HTTPException(status_code=500, detail="Face embedding failed")

        # Upsert person record
        result = await db.execute(select(PersonRecord).where(PersonRecord.id == person_id))
        person = result.scalar_one_or_none()
        if person:
            person.name = name
            person.category = category
            person.risk_level = risk_level
            person.access_zones = access_zones
        else:
            person = PersonRecord(
                id=person_id, name=name, category=category,
                risk_level=risk_level, access_zones=access_zones,
                embedding_path=os.path.join("ml/embeddings", f"{person_id}.npy"),
                watchlist=(category == "Suspect"),
            )
            db.add(person)

        # Audit log
        log = AuditLog(user_id=current_user["username"], action="register_face",
                       resource_type="person", resource_id=person_id)
        db.add(log)
        await db.commit()

        return FaceRegisterResponse(success=True, person_id=person_id,
                                     message=f"Face registered for {name}")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


@router.delete("/persons/{person_id}")
async def delete_person(
    person_id: str,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """GDPR Right to Erasure — spec section 14. Admin only."""
    result = await delete_person_data(person_id, db)
    log = AuditLog(user_id=current_user["username"], action="gdpr_erasure",
                   resource_type="person", resource_id=person_id)
    db.add(log)
    await db.commit()
    return result


def _person_to_dict(p: PersonRecord) -> dict:
    return {
        "id": p.id, "name": p.name, "category": p.category,
        "risk_level": p.risk_level, "access_zones": p.access_zones,
        "watchlist": p.watchlist, "visit_count_24h": p.visit_count_24h,
        "first_seen": p.first_seen.isoformat() if p.first_seen else None,
        "last_seen": p.last_seen.isoformat() if p.last_seen else None,
        "presence_duration_seconds": p.presence_duration_seconds,
        "confidence_trace": p.confidence_trace or [],
        "registered_at": p.registered_at.isoformat() if p.registered_at else None,
    }
