from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
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


def test_delete_item_predictions_uses_index_and_delete() -> None:
    client = SimpleNamespace(
        set=AsyncMock(),
        get=AsyncMock(),
        delete=AsyncMock(),
        smembers=AsyncMock(return_value={"prediction:simple:item:5", "prediction:sync:item:5:abc"}),
    )
    storage = PredictionCacheStorage(client=client)

    asyncio.run(storage.delete_item_predictions(5))

    client.smembers.assert_awaited_once_with("prediction:item:index:5")
    args, _kwargs = client.delete.await_args
    assert "prediction:simple:item:5" in args
    assert "prediction:sync:item:5:abc" in args
    assert "prediction:item:index:5" in args


def test_set_moderation_result_calls_redis_with_ttl() -> None:
    client = AsyncMock()
    storage = PredictionCacheStorage(client=client, ttl_seconds=321)
    result = {
        "id": 13,
        "item_id": 5,
        "status": "completed",
        "is_violation": False,
        "probability": 0.1,
        "error_message": None,
    }

    asyncio.run(storage.set_moderation_result(13, result))

    client.set.assert_awaited_once()
    args, kwargs = client.set.await_args
    assert args[0] == "prediction:moderation:task:13"
    assert kwargs["ex"] == 321


def test_delete_moderation_result_calls_redis_delete() -> None:
    client = AsyncMock()
    storage = PredictionCacheStorage(client=client)

    asyncio.run(storage.delete_moderation_result(21))

    client.delete.assert_awaited_once_with("prediction:moderation:task:21")
