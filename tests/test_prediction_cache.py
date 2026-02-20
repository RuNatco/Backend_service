from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from storages.prediction_cache import PredictionCacheStorage


def test_set_sync_prediction_calls_redis_with_ttl() -> None:
    client = AsyncMock()
    storage = PredictionCacheStorage(client=client, ttl_seconds=123)

    payload = {
        "seller_id": 10,
        "is_verified_seller": False,
        "item_id": 42,
        "description": "x",
        "category": 1,
        "images_qty": 2,
    }
    result = {"is_violation": True, "probability": 0.8}
    asyncio.run(storage.set_sync_prediction(item_id=42, payload=payload, result=result))

    assert client.set.await_count == 1
    args, kwargs = client.set.await_args
    assert args[0].startswith("prediction:sync:item:42:")
    assert kwargs["ex"] == 123


def test_get_simple_prediction_returns_none_on_cache_miss() -> None:
    client = AsyncMock()
    client.get.return_value = None
    storage = PredictionCacheStorage(client=client)

    value = asyncio.run(storage.get_simple_prediction(7))

    assert value is None
    client.get.assert_awaited_once_with("prediction:simple:item:7")


def test_delete_item_predictions_uses_scan_and_delete() -> None:
    client = SimpleNamespace(
        set=AsyncMock(),
        get=AsyncMock(),
        delete=AsyncMock(),
    )

    async def iter_keys():
        for key in ["prediction:simple:item:5", "prediction:sync:item:5:abc"]:
            yield key

    client.scan_iter = MagicMock(side_effect=lambda match: iter_keys())
    storage = PredictionCacheStorage(client=client)

    asyncio.run(storage.delete_item_predictions(5))

    client.scan_iter.assert_called_once_with(match="prediction:*:item:5*")
    client.delete.assert_awaited_once_with(
        "prediction:simple:item:5",
        "prediction:sync:item:5:abc",
    )
