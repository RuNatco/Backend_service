from dataclasses import dataclass
from typing import Mapping, Any, Sequence

from db.connection import get_connection, DB_PATH
from errors import UserNotFoundError
from models.users import UserModel


def _row_to_user(row: Any) -> UserModel:
    if row is None:
        raise UserNotFoundError()
    data = dict(row)
    data["is_active"] = bool(data["is_active"])
    data["is_verified_seller"] = bool(data["is_verified_seller"])
    return UserModel(**data)


@dataclass(frozen=True)
class UserRepository:
    db_path: Any = DB_PATH

    async def create(
        self,
        name: str,
        password: str,
        email: str,
        is_verified_seller: bool = False,
    ) -> UserModel:
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO users (name, password, email, is_verified_seller) VALUES (?, ?, ?, ?)",
                (name, password, email, int(is_verified_seller)),
            )
            conn.commit()
            user_id = cursor.lastrowid
        return await self.get(user_id)

    async def get_by_name_and_password(self, name: str, password: str) -> UserModel:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE name = ? AND password = ? LIMIT 1",
                (name, password),
            ).fetchone()
        return _row_to_user(row)

    async def get(self, user_id: int) -> UserModel:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ? LIMIT 1",
                (user_id,),
            ).fetchone()
        return _row_to_user(row)

    async def delete(self, user_id: int) -> UserModel:
        user = await self.get(user_id)
        with get_connection(self.db_path) as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        return user

    async def update(self, user_id: int, **changes: Mapping[str, Any]) -> UserModel:
        if not changes:
            return await self.get(user_id)

        fields = ", ".join(f"{key} = ?" for key in changes.keys())
        values = list(changes.values()) + [user_id]
        with get_connection(self.db_path) as conn:
            conn.execute(f"UPDATE users SET {fields} WHERE id = ?", values)
            conn.commit()
        return await self.get(user_id)

    async def get_many(self) -> Sequence[UserModel]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM users").fetchall()
        return [_row_to_user(row) for row in rows]
