from __future__ import annotations
import os
from typing import Optional
import redis.asyncio as redis


REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")


class RedisClient:
    def __init__(self, redis_url: str = REDIS_URL) -> None:
        self.redis_url = redis_url
        self._client: Optional[redis.Redis] = None

    async def start(self) -> None:
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
            await self._client.ping()

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("Redis client is not started")
        return self._client
