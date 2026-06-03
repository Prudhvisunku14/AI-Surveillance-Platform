"""Celery report generation task."""
from app.core.celery_app import celery_app


@celery_app.task(name="app.tasks.report_tasks.generate_docx", queue="reports")
def generate_docx(event_data: dict) -> bytes:
    from app.services.report_service import generate_incident_docx
    return generate_incident_docx(event_data)
