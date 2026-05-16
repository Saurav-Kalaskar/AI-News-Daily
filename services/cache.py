"""
Redis wrapper for caching and state persistence.
"""
import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

log = logging.getLogger(__name__)


class Cache:
    """Async Redis cache wrapper."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        await self._redis.ping()
        log.info("  → Redis connected")

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()
            log.info("  → Redis disconnected")

    async def get(self, key: str) -> Optional[str]:
        if not self._redis:
            raise RuntimeError("Redis not connected")
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        if not self._redis:
            raise RuntimeError("Redis not connected")
        await self._redis.set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        if not self._redis:
            raise RuntimeError("Redis not connected")
        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        if not self._redis:
            raise RuntimeError("Redis not connected")
        return await self._redis.exists(key) > 0

    async def keys(self, pattern: str) -> list[str]:
        if not self._redis:
            raise RuntimeError("Redis not connected")
        return [k for k in await self._redis.scan_iter(match=pattern)]

    async def flush(self) -> None:
        if not self._redis:
            raise RuntimeError("Redis not connected")
        await self._redis.flushdb()
