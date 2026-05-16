"""Async database engine and session management for SQLAlchemy 2.0."""
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from settings import Settings

declarative_base = DeclarativeBase


def get_engine():
    settings = Settings()
    return create_async_engine(settings.DATABASE_URL, echo=False, future=True)


AsyncSessionLocal = async_sessionmaker(get_engine(), expire_on_commit=False)
