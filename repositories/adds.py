from dataclasses import dataclass
from typing import Any

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

    async def create(
        self,
        seller_id: int,
        name: str,
        description: str,
        category: int,
        images_qty: int,
    ) -> AddModel:
        with get_connection(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO adds (seller_id, name, description, category, images_qty)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (seller_id, name, description, category, images_qty),
                )
                row = cursor.fetchone()
            conn.commit()
        return _row_to_add(row)

    async def get(self, add_id: int) -> AddModel:
        with get_connection(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM adds WHERE id = %s LIMIT 1",
                    (add_id,),
                )
                row = cursor.fetchone()
        return _row_to_add(row)
