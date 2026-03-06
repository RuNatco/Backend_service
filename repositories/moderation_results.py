from dataclasses import dataclass
import time
from typing import Any, Optional

from app.metrics import observe_db_query_duration
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
    connection_provider: Any = get_connection

    async def create_pending(self, item_id: int) -> ModerationResultModel:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                """
                INSERT INTO moderation_results (item_id, status)
                VALUES ($1, 'pending')
                RETURNING *
                """,
                item_id,
            )
            observe_db_query_duration("insert", started_at)
        return _row_to_result(row)

    async def get(self, task_id: int) -> ModerationResultModel:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                "SELECT * FROM moderation_results WHERE id = $1 LIMIT 1",
                task_id,
            )
            observe_db_query_duration("select", started_at)
        return _row_to_result(row)

    async def get_latest_pending_by_item_id(self, item_id: int) -> ModerationResultModel:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                """
                SELECT * FROM moderation_results
                WHERE item_id = $1 AND status = 'pending'
                ORDER BY id DESC
                LIMIT 1
                """,
                item_id,
            )
            observe_db_query_duration("select", started_at)
        return _row_to_result(row)

    async def mark_completed(
        self,
        task_id: int,
        is_violation: bool,
        probability: float,
    ) -> ModerationResultModel:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                """
                UPDATE moderation_results
                SET status = 'completed',
                    is_violation = $1,
                    probability = $2,
                    error_message = NULL,
                    processed_at = NOW()
                WHERE id = $3
                RETURNING *
                """,
                is_violation,
                probability,
                task_id,
            )
            observe_db_query_duration("update", started_at)
        return _row_to_result(row)

    async def mark_failed(self, task_id: int, error_message: str) -> ModerationResultModel:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                """
                UPDATE moderation_results
                SET status = 'failed',
                    error_message = $1,
                    processed_at = NOW()
                WHERE id = $2
                RETURNING *
                """,
                error_message,
                task_id,
            )
            observe_db_query_duration("update", started_at)
        return _row_to_result(row)

    async def mark_retry(self, task_id: int, error_message: str) -> ModerationResultModel:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            row = await conn.fetchrow(
                """
                UPDATE moderation_results
                SET status = 'pending',
                    error_message = $1
                WHERE id = $2
                RETURNING *
                """,
                error_message,
                task_id,
            )
            observe_db_query_duration("update", started_at)
        return _row_to_result(row)

    async def get_task_ids_by_item_id(self, item_id: int) -> list[int]:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            rows = await conn.fetch(
                "SELECT id FROM moderation_results WHERE item_id = $1 ORDER BY id",
                item_id,
            )
            observe_db_query_duration("select", started_at)
        return [int(row["id"]) for row in rows]

    async def delete_by_item_id(self, item_id: int) -> int:
        async with self.connection_provider(self.dsn) as conn:
            started_at = time.perf_counter()
            result = await conn.execute(
                "DELETE FROM moderation_results WHERE item_id = $1",
                item_id,
            )
            observe_db_query_duration("delete", started_at)
        return int(result.split()[-1])
