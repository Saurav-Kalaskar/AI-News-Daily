"""Shared async session dependency for bot/dao."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.session import AsyncSessionLocal

# Re-use the sessionmaker from db/session
_async_session_local: async_sessionmaker[AsyncSession] = AsyncSessionLocal


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency-injection style async session context manager."""
    async with _async_session_local() as session:
        yield session