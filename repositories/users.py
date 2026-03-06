import json
import os
import time
from dataclasses import dataclass
from typing import Mapping, Any, Sequence, Optional

import redis.asyncio as redis
from app.metrics import observe_db_query_duration
from db.connection import get_connection, DB_DSN
from errors import UserNotFoundError
from models.users import UserModel

USER_CACHE_TTL_SECONDS = int(os.getenv("USER_CACHE_TTL_SECONDS", "3600"))


def _row_to_user(row: Any) -> UserModel:
    if row is None:
        raise UserNotFoundError()
    data = dict(row)
    data["is_active"] = bool(data["is_active"])
    data["is_verified_seller"] = bool(data["is_verified_seller"])
    return UserModel(**data)

class UserRedisStorage:
    def __init__(self, client: redis.Redis, ttl_seconds: int = USER_CACHE_TTL_SECONDS) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _key(user_id: int) -> str:
        return f"user:{user_id}"

    async def get_user(self, user_id: int) -> Optional[UserModel]:
        raw = await self.client.get(self._key(user_id))
        if raw is None:
            return None
        return UserModel(**json.loads(raw))

    async def set_user(self, user: UserModel) -> None:
        payload = user.model_dump() if hasattr(user, "model_dump") else user.dict()
        await self.client.set(
            self._key(user.id),
            json.dumps(payload, ensure_ascii=True),
            ex=self.ttl_seconds,
        )

    async def delete_user(self, user_id: int) -> None:
        await self.client.delete(self._key(user_id))


@dataclass(frozen=True)
class UserRepository:
    dsn: Any = DB_DSN
    connection_provider: Any = get_connection
    user_cache_storage: Optional[UserRedisStorage] = None

    async def create(
        self,
        name: str,
        password: str,
        email: str,
        is_verified_seller: bool = False,
    ) -> UserModel:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                """
                INSERT INTO users (name, password, email, is_verified_seller)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                name,
                password,
                email,
                is_verified_seller,
            )
            observe_db_query_duration("insert", started_at)
        user = _row_to_user(row)
        if self.user_cache_storage is not None:
            await self.user_cache_storage.set_user(user)
        return user

    async def get_by_name_and_password(self, name: str, password: str) -> UserModel:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE name = $1 AND password = $2 LIMIT 1",
                name,
                password,
            )
            observe_db_query_duration("select", started_at)
        user = _row_to_user(row)
        if self.user_cache_storage is not None:
            await self.user_cache_storage.set_user(user)
        return user

    async def get(self, user_id: int) -> UserModel:
        if self.user_cache_storage is not None:
            cached_user = await self.user_cache_storage.get_user(user_id)
            if cached_user is not None:
                return cached_user

        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1 LIMIT 1",
                user_id,
            )
            observe_db_query_duration("select", started_at)
        user = _row_to_user(row)
        if self.user_cache_storage is not None:
            await self.user_cache_storage.set_user(user)
        return user

    async def delete(self, user_id: int) -> UserModel:
        user = await self.get(user_id)
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            await conn.execute("DELETE FROM users WHERE id = $1", user_id)
            observe_db_query_duration("delete", started_at)
        if self.user_cache_storage is not None:
            await self.user_cache_storage.delete_user(user_id)
        return user

    async def update(self, user_id: int, **changes: Mapping[str, Any]) -> UserModel:
        if not changes:
            return await self.get(user_id)

        allowed_fields = {"name", "password", "email", "is_active", "is_verified_seller"}
        invalid_fields = [field for field in changes.keys() if field not in allowed_fields]
        if invalid_fields:
            raise ValueError(f"Unsupported update fields: {', '.join(invalid_fields)}")

        set_clause = ", ".join(f"{field} = ${index}" for index, field in enumerate(changes.keys(), start=1))
        values = list(changes.values())
        user_id_placeholder = f"${len(values) + 1}"

        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                f"UPDATE users SET {set_clause} WHERE id = {user_id_placeholder} RETURNING *",
                *values,
                user_id,
            )
            observe_db_query_duration("update", started_at)
        user = _row_to_user(row)
        if self.user_cache_storage is not None:
            await self.user_cache_storage.set_user(user)
        return user

    async def get_many(self) -> Sequence[UserModel]:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            rows = await conn.fetch("SELECT * FROM users")
            observe_db_query_duration("select", started_at)
        return [_row_to_user(row) for row in rows]
