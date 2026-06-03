"""Celery GenAI task — async LLM summary generation."""
from app.core.celery_app import celery_app


@celery_app.task(name="app.tasks.genai_tasks.generate_summary", queue="genai")
def generate_summary(event_id: str, event_data: dict):
    import asyncio
    from app.services.genai_service import generate_incident_summary

    async def _run():
        return await generate_incident_summary(event_data)

    result = asyncio.run(_run())
    return result
