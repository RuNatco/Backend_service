import asyncio
from unittest.mock import AsyncMock, MagicMock

from models.users import UserModel
from repositories.users import UserRepository

RAW_USER = {
    "id": 5,
    "name": "Cached User",
    "password": "pass",
    "email": "cached_user@example.com",
    "is_active": True,
    "is_verified_seller": True,
}

RAW_DB_USER = {
    "id": 6,
    "name": "From DB",
    "password": "pass",
    "email": "db@example.com",
    "is_active": True,
    "is_verified_seller": False,
}

RAW_UPDATED_DB_USER = {
    **RAW_DB_USER,
    "name": "Updated User",
    "email": "updated@example.com",
}


def _connection_provider_with_row(row: dict) -> MagicMock:
    connection = MagicMock()
    connection.fetchrow = AsyncMock(return_value=row)
    connection.fetch = AsyncMock(return_value=[row])
    connection.execute = AsyncMock(return_value="DELETE 1")

    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=connection)
    context_manager.__aexit__ = AsyncMock(return_value=None)

    return MagicMock(return_value=context_manager)


def test_user_repository_get_cache_hit() -> None:
    cache = MagicMock()
    cache.get_user = AsyncMock(return_value=UserModel(**RAW_USER))
    cache.set_user = AsyncMock()

    connection_provider = MagicMock()
    user_repo = UserRepository(connection_provider=connection_provider, user_cache_storage=cache)
    user = asyncio.run(user_repo.get(5))

    assert user.id == 5
    cache.get_user.assert_awaited_once_with(5)
    connection_provider.assert_not_called()
    cache.set_user.assert_not_awaited()


def test_user_repository_get_cache_miss_sets_cache() -> None:
    cache = MagicMock()
    cache.get_user = AsyncMock(return_value=None)
    cache.set_user = AsyncMock()

    connection_provider = _connection_provider_with_row(RAW_DB_USER)
    user_repo = UserRepository(connection_provider=connection_provider, user_cache_storage=cache)
    user = asyncio.run(user_repo.get(6))

    assert user.id == 6
    cache.get_user.assert_awaited_once_with(6)
    connection_provider.assert_called_once_with(user_repo.dsn)
    cache.set_user.assert_awaited_once()


def test_user_repository_update_refreshes_cache() -> None:
    cache = MagicMock()
    cache.get_user = AsyncMock(return_value=None)
    cache.set_user = AsyncMock()

    connection_provider = _connection_provider_with_row(RAW_UPDATED_DB_USER)
    user_repo = UserRepository(connection_provider=connection_provider, user_cache_storage=cache)
    user = asyncio.run(user_repo.update(6, name="Updated User"))

    assert user.name == "Updated User"
    cache.set_user.assert_awaited_once()


def test_user_repository_delete_invalidates_cache() -> None:
    cache = MagicMock()
    cache.get_user = AsyncMock(return_value=UserModel(**RAW_USER))
    cache.set_user = AsyncMock()
    cache.delete_user = AsyncMock()

    connection_provider = _connection_provider_with_row(RAW_USER)
    user_repo = UserRepository(connection_provider=connection_provider, user_cache_storage=cache)
    deleted_user = asyncio.run(user_repo.delete(5))

    assert deleted_user.id == 5
    cache.delete_user.assert_awaited_once_with(5)
