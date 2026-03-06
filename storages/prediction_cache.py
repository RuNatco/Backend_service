from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Optional

import redis.asyncio as redis

CACHE_TTL_SECONDS = int(os.getenv("PREDICTION_CACHE_TTL_SECONDS", "3600"))


class PredictionCacheStorage:
    def __init__(self, client: redis.Redis, ttl_seconds: int = CACHE_TTL_SECONDS) -> None:
        self.client = client
        # TTL 1 час: снижает нагрузку на БД/модель при повторных запросах,
        # но не хранит результат слишком долго, чтобы кэш не устаревал.
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _sync_key(item_id: int, payload: dict[str, Any]) -> str:
        payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        return f"prediction:sync:item:{item_id}:{payload_hash}"

    @staticmethod
    def _simple_key(item_id: int) -> str:
        return f"prediction:simple:item:{item_id}"

    @staticmethod
    def _moderation_task_key(task_id: int) -> str:
        return f"prediction:moderation:task:{task_id}"

    @staticmethod
    def _item_index_key(item_id: int) -> str:
        return f"prediction:item:index:{item_id}"

    async def get_sync_prediction(
        self,
        *,
        item_id: int,
        payload: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        raw = await self.client.get(self._sync_key(item_id, payload))
        return json.loads(raw) if raw else None

    async def set_sync_prediction(
        self,
        *,
        item_id: int,
        payload: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        cache_key = self._sync_key(item_id, payload)
        await self.client.set(
            cache_key,
            json.dumps(result, ensure_ascii=True),
            ex=self.ttl_seconds,
        )
        await self.client.sadd(self._item_index_key(item_id), cache_key)
        await self.client.expire(self._item_index_key(item_id), self.ttl_seconds)

    async def get_simple_prediction(self, item_id: int) -> Optional[dict[str, Any]]:
        raw = await self.client.get(self._simple_key(item_id))
        return json.loads(raw) if raw else None

    async def set_simple_prediction(self, item_id: int, result: dict[str, Any]) -> None:
        cache_key = self._simple_key(item_id)
        await self.client.set(
            cache_key,
            json.dumps(result, ensure_ascii=True),
            ex=self.ttl_seconds,
        )
        await self.client.sadd(self._item_index_key(item_id), cache_key)
        await self.client.expire(self._item_index_key(item_id), self.ttl_seconds)

    async def get_moderation_result(self, task_id: int) -> Optional[dict[str, Any]]:
        raw = await self.client.get(self._moderation_task_key(task_id))
        return json.loads(raw) if raw else None

    async def set_moderation_result(self, task_id: int, result: dict[str, Any]) -> None:
        await self.client.set(
            self._moderation_task_key(task_id),
            json.dumps(result, ensure_ascii=True),
            ex=self.ttl_seconds,
        )

    async def delete_moderation_result(self, task_id: int) -> None:
        await self.client.delete(self._moderation_task_key(task_id))

    async def delete_item_predictions(self, item_id: int) -> None:
        index_key = self._item_index_key(item_id)
        keys = list(await self.client.smembers(index_key))
        if keys:
            await self.client.delete(*keys, index_key)
        else:
            await self.client.delete(index_key)
