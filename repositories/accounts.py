from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from db.connection import DB_DSN, get_connection
from errors import AccountNotFoundError
from models.accounts import AccountModel


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def _row_to_account(row: Any) -> AccountModel:
    if row is None:
        raise AccountNotFoundError()
    return AccountModel(**dict(row))


@dataclass(frozen=True)
class AccountRepository:
    dsn: Any = DB_DSN
    connection_provider: Any = get_connection

    async def create(self, login: str, password: str) -> AccountModel:
        async with self.connection_provider(self.dsn) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO account (login, password)
                VALUES ($1, $2)
                RETURNING *
                """,
                login,
                hash_password(password),
            )
        return _row_to_account(row)

    async def get(self, account_id: int) -> AccountModel:
        async with self.connection_provider(self.dsn) as conn:
            row = await conn.fetchrow(
                "SELECT * FROM account WHERE id = $1 LIMIT 1",
                account_id,
            )
        return _row_to_account(row)

    async def delete(self, account_id: int) -> AccountModel:
        account = await self.get(account_id)
        async with self.connection_provider(self.dsn) as conn:
            await conn.execute("DELETE FROM account WHERE id = $1", account_id)
        return account

    async def block(self, account_id: int) -> AccountModel:
        async with self.connection_provider(self.dsn) as conn:
            row = await conn.fetchrow(
                """
                UPDATE account
                SET is_blocked = TRUE
                WHERE id = $1
                RETURNING *
                """,
                account_id,
            )
        return _row_to_account(row)

    async def get_by_login_and_password(self, login: str, password: str) -> AccountModel:
        async with self.connection_provider(self.dsn) as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM account
                WHERE login = $1 AND password = $2
                LIMIT 1
                """,
                login,
                hash_password(password),
            )
        return _row_to_account(row)
