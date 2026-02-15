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
    connection_provider: Any = get_connection

    async def create(
        self,
        seller_id: int,
        name: str,
        description: str,
        category: int,
        images_qty: int,
    ) -> AddModel:
        with self.connection_provider(self.dsn) as conn:
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
        with self.connection_provider(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM adds WHERE id = %s LIMIT 1",
                    (add_id,),
                )
                row = cursor.fetchone()
        return _row_to_add(row)

    async def get_with_seller(self, add_id: int) -> dict[str, Any]:
        with self.connection_provider(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
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
                    WHERE a.id = %s
                    LIMIT 1
                    """,
                    (add_id,),
                )
                row = cursor.fetchone()
        if row is None:
            raise AddNotFoundError()
        return dict(row)
