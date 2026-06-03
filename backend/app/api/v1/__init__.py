"""API v1 router — all spec endpoints."""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, videos, events, persons, sensors, websocket, reports, health

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(videos.router)
api_router.include_router(events.router)
api_router.include_router(persons.router)
api_router.include_router(sensors.router)
api_router.include_router(websocket.router)
api_router.include_router(reports.router)
api_router.include_router(health.router)
