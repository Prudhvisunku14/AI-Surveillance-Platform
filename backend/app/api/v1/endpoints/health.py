"""Health check endpoint — spec section 11."""
from fastapi import APIRouter
from app.schemas.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    # Database
    db_status = "ok"
    try:
        from app.db.database import engine
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_status = "degraded"

    # Redis
    redis_status = "ok"
    try:
        from app.db.redis_client import get_redis
        r = await get_redis()
        await r.ping()
    except Exception:
        redis_status = "unavailable"

    # YOLO
    yolo_status = "ok"
    try:
        from app.services.detector import PersonDetector
        d = PersonDetector()
        yolo_status = "ok" if d.is_available() else "fallback_mode"
    except Exception:
        yolo_status = "unavailable"

    # GenAI
    from app.core.config import get_settings
    s = get_settings()
    genai_status = "enabled" if (s.genai_enabled and s.openai_api_key) else "rule_based_fallback"

    overall = "ok" if db_status == "ok" else "degraded"

    return HealthResponse(
        status=overall, database=db_status,
        redis=redis_status, yolo=yolo_status, genai=genai_status,
    )
