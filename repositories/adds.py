from dataclasses import dataclass
import time
from typing import Any

from app.metrics import observe_db_query_duration
from db.connection import get_connection, DB_DSN
from errors import AddNotFoundError
from models.adds import AddModel


def _row_to_add(row: Any) -> AddModel:
    if row is None:
        raise AddNotFoundError()
    return AddModel(**dict(row))


@dataclass(frozen=True)
class AddRepository:
    dsn: Any = DB_DSN
    connection_provider: Any = get_connection

    async def create(
        self,
        seller_id: int,
        name: str,
        description: str,
        category: int,
        images_qty: int,
    ) -> AddModel:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                """
                INSERT INTO adds (seller_id, name, description, category, images_qty)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                seller_id,
                name,
                description,
                category,
                images_qty,
            )
            observe_db_query_duration("insert", started_at)
        return _row_to_add(row)

    async def get(self, add_id: int) -> AddModel:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                "SELECT * FROM adds WHERE id = $1 LIMIT 1",
                add_id,
            )
            observe_db_query_duration("select", started_at)
        return _row_to_add(row)

    async def get_with_seller(self, add_id: int) -> dict[str, Any]:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                """
                SELECT
                    a.id AS add_id,
                    a.description,
                    a.category,
                    a.images_qty,
                    u.id AS seller_id,
                    u.is_verified_seller
                FROM adds a
                JOIN users u ON u.id = a.seller_id
                WHERE a.id = $1
                LIMIT 1
                """,
                add_id,
            )
            observe_db_query_duration("select", started_at)
        if row is None:
            raise AddNotFoundError()
        return dict(row)

    async def delete(self, add_id: int) -> AddModel:
        add = await self.get(add_id)
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            await conn.execute("DELETE FROM adds WHERE id = $1", add_id)
            observe_db_query_duration("delete", started_at)
        return add
