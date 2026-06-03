"""
MongoDB async client setup using Motor.
Used for flexible person cards and face registry storage.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import get_settings

settings = get_settings()

_client: AsyncIOMotorClient = None
_db: AsyncIOMotorDatabase = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        client = get_mongo_client()
        _db = client["surveillance"]
    return _db


async def get_mongo() -> AsyncIOMotorDatabase:
    yield get_mongo_db()


async def init_mongo_indexes() -> None:
    """Create indexes for performance."""
    db = get_mongo_db()
    # Persons collection indexes
    await db.persons.create_index("person_id", unique=True)
    await db.persons.create_index("category")
    await db.persons.create_index("risk_level")
    # Face registry indexes
    await db.face_registry.create_index("person_id", unique=True)
    # Sensor events indexes
    await db.sensor_events.create_index("event_id", unique=True)
    await db.sensor_events.create_index("timestamp")
    await db.sensor_events.create_index("location_id")
