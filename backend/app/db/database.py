"""SQLite async database — spec section 15: use SQLite for assignment."""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass

# Ensure all model metadata is loaded before creating tables
# Import models so that they are registered with Base.metadata
from app.models import sql_models  # noqa: F401


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        # create_all only creates tables that don't already exist —
        # it will NOT drop or wipe existing data.
        await conn.run_sync(Base.metadata.create_all)
