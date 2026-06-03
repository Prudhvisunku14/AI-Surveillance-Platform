"""Redis client for cache and WebSocket pub/sub."""
import json
import redis.asyncio as aioredis
from app.core.config import get_settings

settings = get_settings()
_redis_client = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def publish_event(channel: str, data: dict):
    r = await get_redis()
    await r.publish(channel, json.dumps(data))


async def cache_set(key: str, value: dict, ttl: int = 300):
    r = await get_redis()
    await r.setex(key, ttl, json.dumps(value))


async def cache_get(key: str) -> dict | None:
    r = await get_redis()
    data = await r.get(key)
    return json.loads(data) if data else None
