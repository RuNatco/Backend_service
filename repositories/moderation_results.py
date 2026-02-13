from dataclasses import dataclass
from typing import Any, Optional

from db.connection import DB_DSN, get_connection
from errors import ModerationTaskNotFoundError
from models.moderation_results import ModerationResultModel


def _row_to_result(row: Any) -> ModerationResultModel:
    if row is None:
        raise ModerationTaskNotFoundError()
    return ModerationResultModel(**dict(row))


@dataclass(frozen=True)
class ModerationResultRepository:
    dsn: Any = DB_DSN

    async def create_pending(self, item_id: int) -> ModerationResultModel:
        with get_connection(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO moderation_results (item_id, status)
                    VALUES (%s, 'pending')
                    RETURNING *
                    """,
                    (item_id,),
                )
                row = cursor.fetchone()
            conn.commit()
        return _row_to_result(row)

    async def get(self, task_id: int) -> ModerationResultModel:
        with get_connection(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM moderation_results WHERE id = %s LIMIT 1",
                    (task_id,),
                )
                row = cursor.fetchone()
        return _row_to_result(row)

    async def get_latest_pending_by_item_id(self, item_id: int) -> ModerationResultModel:
        with get_connection(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM moderation_results
                    WHERE item_id = %s AND status = 'pending'
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (item_id,),
                )
                row = cursor.fetchone()
        return _row_to_result(row)

    async def mark_completed(
        self,
        task_id: int,
        is_violation: bool,
        probability: float,
    ) -> ModerationResultModel:
        with get_connection(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE moderation_results
                    SET status = 'completed',
                        is_violation = %s,
                        probability = %s,
                        error_message = NULL,
                        processed_at = NOW()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (is_violation, probability, task_id),
                )
                row = cursor.fetchone()
            conn.commit()
        return _row_to_result(row)

    async def mark_failed(self, task_id: int, error_message: str) -> ModerationResultModel:
        with get_connection(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE moderation_results
                    SET status = 'failed',
                        error_message = %s,
                        processed_at = NOW()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (error_message, task_id),
                )
                row = cursor.fetchone()
            conn.commit()
        return _row_to_result(row)

    async def mark_retry(self, task_id: int, error_message: str) -> ModerationResultModel:
        with get_connection(self.dsn) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE moderation_results
                    SET status = 'pending',
                        error_message = %s
                    WHERE id = %s
                    RETURNING *
                    """,
                    (error_message, task_id),
                )
                row = cursor.fetchone()
            conn.commit()
        return _row_to_result(row)
