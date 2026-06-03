"""Reports endpoints — DOCX incident + CSV export, spec section 11 + 13."""
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.models.sql_models import EventRecord, AuditLog
from app.services.report_service import generate_incident_docx, generate_events_csv

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/incident/{event_id}")
async def download_incident_report(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download DOCX incident report — spec section 11."""
    if current_user["role"] not in ("analyst", "admin"):
        raise HTTPException(status_code=403, detail="Analyst or Admin required")

    result = await db.execute(select(EventRecord).where(EventRecord.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event_dict = {
        "event_id": event.id, "video_id": event.video_id,
        "event_type": event.event_type, "severity": event.severity,
        "timestamp": str(event.timestamp), "threat_score": event.threat_score,
        "zone_id": event.zone_id, "persons_involved": event.persons_involved or [],
        "threat_features": event.threat_features,
        "genai_data": event.genai_data, "acknowledged": event.acknowledged,
    }

    docx_bytes = generate_incident_docx(event_dict)

    # Audit log
    log = AuditLog(user_id=current_user["username"], action="download_report",
                   resource_type="event", resource_id=event_id)
    db.add(log)
    await db.commit()

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=incident_{event_id}.docx"},
    )


@router.get("/events/export")
async def export_events_csv(
    severity: Optional[str] = Query(None),
    video_id: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export event log as CSV — spec section 11."""
    q = select(EventRecord).order_by(EventRecord.timestamp.desc())
    if severity:
        q = q.where(EventRecord.severity == severity)
    if video_id:
        q = q.where(EventRecord.video_id == video_id)
    if acknowledged is not None:
        q = q.where(EventRecord.acknowledged == acknowledged)

    result = await db.execute(q)
    events = result.scalars().all()

    events_dicts = [{
        "event_id": e.id, "video_id": e.video_id, "event_type": e.event_type,
        "severity": e.severity, "threat_score": e.threat_score,
        "timestamp": e.timestamp, "zone_id": e.zone_id,
        "persons_involved": e.persons_involved or [],
        "acknowledged": e.acknowledged, "acknowledged_by": e.acknowledged_by,
        "acknowledged_at": e.acknowledged_at,
        "genai_data": e.genai_data,
    } for e in events]

    csv_content = generate_events_csv(events_dicts)

    # Audit log
    log = AuditLog(user_id=current_user["username"], action="export_csv",
                   resource_type="events")
    db.add(log)
    await db.commit()

    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=events_export.csv"},
    )
