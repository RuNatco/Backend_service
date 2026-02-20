import json
import os
from dataclasses import dataclass
from typing import Mapping, Any, Sequence, Optional

import redis.asyncio as redis
from db.connection import get_connection, DB_DSN
from errors import UserNotFoundError
from models.users import UserModel

USER_CACHE_TTL_SECONDS = int(os.getenv("USER_CACHE_TTL_SECONDS", "300"))


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
        with self.connection_provider(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (name, password, email, is_verified_seller)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *
                    """,
                    (name, password, email, is_verified_seller),
                )
                row = cursor.fetchone()
            conn.commit()
        user = _row_to_user(row)
        if self.user_cache_storage is not None:
            await self.user_cache_storage.set_user(user)
        return user

    async def get_by_name_and_password(self, name: str, password: str) -> UserModel:
        with self.connection_provider(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE name = %s AND password = %s LIMIT 1",
                    (name, password),
                )
                row = cursor.fetchone()
        user = _row_to_user(row)
        if self.user_cache_storage is not None:
            await self.user_cache_storage.set_user(user)
        return user

    async def get(self, user_id: int) -> UserModel:
        if self.user_cache_storage is not None:
            cached_user = await self.user_cache_storage.get_user(user_id)
            if cached_user is not None:
                return cached_user

        with self.connection_provider(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE id = %s LIMIT 1",
                    (user_id,),
                )
                row = cursor.fetchone()
        user = _row_to_user(row)
        if self.user_cache_storage is not None:
            await self.user_cache_storage.set_user(user)
        return user

    async def delete(self, user_id: int) -> UserModel:
        user = await self.get(user_id)
        with self.connection_provider(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
        if self.user_cache_storage is not None:
            await self.user_cache_storage.delete_user(user_id)
        return user

    async def update(self, user_id: int, **changes: Mapping[str, Any]) -> UserModel:
        if not changes:
            return await self.get(user_id)

        fields = ", ".join(f"{key} = %s" for key in changes.keys())
        values = list(changes.values()) + [user_id]
        with self.connection_provider(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"UPDATE users SET {fields} WHERE id = %s", values)
            conn.commit()
        user = await self.get(user_id)
        if self.user_cache_storage is not None:
            await self.user_cache_storage.set_user(user)
        return user

    async def get_many(self) -> Sequence[UserModel]:
        with self.connection_provider(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users")
                rows = cursor.fetchall()
        return [_row_to_user(row) for row in rows]
