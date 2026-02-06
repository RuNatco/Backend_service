from dataclasses import dataclass
from typing import Any

from db.connection import get_connection, DB_PATH
from errors import AddNotFoundError
from models.adds import AddModel


def _row_to_add(row: Any) -> AddModel:
    if row is None:
        raise AddNotFoundError()
    return AddModel(**dict(row))


@dataclass(frozen=True)
class AddRepository:
    db_path: Any = DB_PATH

    async def create(
        self,
        seller_id: int,
        name: str,
        description: str,
        category: int,
        images_qty: int,
    ) -> AddModel:
        with get_connection(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO adds (seller_id, name, description, category, images_qty)
                VALUES (?, ?, ?, ?, ?)
                """,
                (seller_id, name, description, category, images_qty),
            )
            conn.commit()
            add_id = cursor.lastrowid
        return await self.get(add_id)

    async def get(self, add_id: int) -> AddModel:
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM adds WHERE id = ? LIMIT 1",
                (add_id,),
            ).fetchone()
        return _row_to_add(row)
