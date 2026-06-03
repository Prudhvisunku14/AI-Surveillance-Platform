"""Events endpoints — exact spec routes section 11."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.sql_models import EventRecord, AuditLog
from app.schemas.schemas import AcknowledgeRequest, AcknowledgeResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
async def list_events(
    severity: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    person_id: Optional[str] = Query(None),
    video_id: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    min_threat_score: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List events with filters — spec section 11."""
    q = select(EventRecord).order_by(EventRecord.threat_score.desc(), EventRecord.timestamp.desc())

    if severity:
        q = q.where(EventRecord.severity == severity)
    if event_type:
        q = q.where(EventRecord.event_type == event_type)
    if video_id:
        q = q.where(EventRecord.video_id == video_id)
    if acknowledged is not None:
        q = q.where(EventRecord.acknowledged == acknowledged)
    if min_threat_score is not None:
        q = q.where(EventRecord.threat_score >= min_threat_score)

    count_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar()

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    events = result.scalars().all()

    return {
        "items": [_event_to_dict(e) for e in events],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{event_id}")
async def get_event(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get single event with full GenAI summary — spec section 11."""
    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return _event_to_dict(event)


@router.post("/{event_id}/acknowledge", response_model=AcknowledgeResponse)
async def acknowledge_event(
    event_id: str,
    body: AcknowledgeRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge event — spec section 11. Analyst+ only."""
    if current_user["role"] not in ("analyst", "admin"):
        raise HTTPException(status_code=403, detail="Analyst or Admin role required")

    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    now = datetime.now(timezone.utc)
    event.acknowledged = True
    event.acknowledged_by = body.analyst_name
    event.acknowledged_at = now

    # Audit log — spec: all user actions logged
    log = AuditLog(user_id=current_user["username"], action="acknowledge_event",
                   resource_type="event", resource_id=event_id,
                   details={"analyst_name": body.analyst_name})
    db.add(log)
    await db.commit()

    return AcknowledgeResponse(success=True, acknowledged_by=body.analyst_name,
                                acknowledged_at=now)


def _event_to_dict(e: EventRecord) -> dict:
    return {
        "event_id": e.id,
        "video_id": e.video_id,
        "event_type": e.event_type,
        "severity": e.severity,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "frame_index": e.frame_index,
        "frame_snapshot_path": e.frame_snapshot_path,
        "persons_involved": e.persons_involved or [],
        "threat_score": e.threat_score,
        "threat_features": e.threat_features,
        "threat_explainability": e.threat_explainability,
        "genai_summary": e.genai_summary,
        "genai_data": e.genai_data,
        "acknowledged": e.acknowledged,
        "acknowledged_by": e.acknowledged_by,
        "acknowledged_at": e.acknowledged_at.isoformat() if e.acknowledged_at else None,
        "zone_id": e.zone_id,
    }
