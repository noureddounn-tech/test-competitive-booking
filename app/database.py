from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# NullPool: avoids reusing asyncpg connections across event loops (each pytest
# TestClient run gets its own loop), and gives concurrency tests genuinely
# independent connections rather than ones queued behind a shared pool.
engine = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
