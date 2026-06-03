"""Sensor ingest endpoint — spec section 11."""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.sql_models import SensorEventRecord, EventRecord
from app.schemas.schemas import SensorEventIn, SensorIngestResponse
from app.services.event_engine import EventDetectionEngine
from app.db.redis_client import publish_event

router = APIRouter(prefix="/sensor", tags=["sensors"])


@router.post("/ingest", response_model=SensorIngestResponse)
async def ingest_sensor_events(
    events: List[SensorEventIn],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk ingest sensor events — spec section 4.2."""
    ingested = 0
    anomalies = 0
    engine = EventDetectionEngine(video_id="SENSOR")

    for se in events:
        # Check for duplicate
        existing = await db.execute(
            select(SensorEventRecord).where(SensorEventRecord.event_id == se.event_id)
        )
        if existing.scalar_one_or_none():
            continue

        record = SensorEventRecord(
            event_id=se.event_id,
            timestamp=se.timestamp,
            sensor_type=se.sensor_type,
            location_id=se.location_id,
            event=se.event,
            authorized=se.authorized,
            person_id=se.person_id,
            confidence=se.confidence,
            anomaly_flag=se.anomaly_flag,
        )
        db.add(record)
        ingested += 1

        if se.anomaly_flag:
            anomalies += 1
            # Generate sensor_mismatch event
            ev = engine.check_sensor_mismatch(se.event_id, se.location_id)
            db_ev = EventRecord(
                id=ev["event_id"],
                event_type=ev["event_type"],
                severity=ev["severity"],
                timestamp=datetime.now(timezone.utc),
                threat_score=ev["threat_score"],
                threat_features=ev["threat_features"],
                threat_explainability=ev["threat_explainability"],
                zone_id=se.location_id,
                metadata_extra={"sensor_event_id": se.event_id,
                                 "sensor_type": se.sensor_type},
            )
            db.add(db_ev)
            try:
                await publish_event("alerts", ev)
            except Exception:
                pass

    await db.commit()
    return SensorIngestResponse(ingested=ingested, anomalies_detected=anomalies)
