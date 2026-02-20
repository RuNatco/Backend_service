import asyncio
import json
from unittest.mock import AsyncMock

from models.users import UserModel
from repositories.users import UserRedisStorage

RAW_USER = {
    "id": 5,
    "name": "Cached User",
    "password": "pass",
    "email": "cached_user@example.com",
    "is_active": True,
    "is_verified_seller": True,
}

UNIT_USER = UserModel(
    id=11,
    name="Unit User",
    password="secret",
    email="unit_user@example.com",
    is_active=True,
    is_verified_seller=False,
)


def test_get_user_cache_miss_returns_none() -> None:
    client = AsyncMock()
    client.get.return_value = None
    storage = UserRedisStorage(client=client, ttl_seconds=100)
    user = asyncio.run(storage.get_user(7))

    assert user is None
    client.get.assert_awaited_once_with("user:7")


def test_set_user_writes_json_with_ttl() -> None:
    client = AsyncMock()
    storage = UserRedisStorage(client=client, ttl_seconds=123)
    asyncio.run(storage.set_user(UNIT_USER))
    client.set.assert_awaited_once()
    args, kwargs = client.set.await_args
    assert args[0] == "user:11"
    payload = json.loads(args[1])
    assert payload["id"] == 11
    assert payload["name"] == "Unit User"
    assert kwargs["ex"] == 123


def test_get_user_cache_hit_returns_model() -> None:
    client = AsyncMock()
    client.get.return_value = json.dumps(RAW_USER)
    storage = UserRedisStorage(client=client)
    user = asyncio.run(storage.get_user(5))

    assert user is not None
    assert user.id == 5
    assert user.name == "Cached User"
    assert user.is_verified_seller is True


def test_delete_user_calls_redis_delete() -> None:
    client = AsyncMock()
    storage = UserRedisStorage(client=client)
    asyncio.run(storage.delete_user(3))

    client.delete.assert_awaited_once_with("user:3")



