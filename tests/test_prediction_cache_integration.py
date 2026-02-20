from __future__ import annotations

import asyncio

import pytest
import redis.asyncio as redis

from storages.prediction_cache import PredictionCacheStorage

pytestmark = pytest.mark.integration


def test_prediction_cache_roundtrip_integration() -> None:
    async def _scenario() -> tuple[bool, dict[str, object] | None]:
        client = redis.from_url("redis://127.0.0.1:6379/0", decode_responses=True)
        try:
            try:
                await client.ping()
            except Exception:
                return False, None

            storage = PredictionCacheStorage(client=client, ttl_seconds=60)
            payload = {
                "seller_id": 1,
                "is_verified_seller": False,
                "item_id": 22,
                "description": "abc",
                "category": 10,
                "images_qty": 1,
            }
            result = {"is_violation": False, "probability": 0.2}

            await storage.set_sync_prediction(item_id=22, payload=payload, result=result)
            cached = await storage.get_sync_prediction(item_id=22, payload=payload)
            await storage.delete_item_predictions(22)
            return True, cached
        finally:
            await client.aclose()

    ok, cached = asyncio.run(_scenario())
    if not ok:
        pytest.skip("Redis is unavailable for integration test")
    assert cached == {"is_violation": False, "probability": 0.2}
