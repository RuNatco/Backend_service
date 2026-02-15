from dataclasses import dataclass
from typing import Any

from errors import (
    AddNotFoundError,
    KafkaUnavailableError,
    ModerationEnqueueError,
    ModerationTaskNotFoundError,
)
from repositories.adds import AddRepository
from repositories.moderation_results import ModerationResultRepository


@dataclass(frozen=True)
class ModerationService:
    add_repo: AddRepository = AddRepository()
    moderation_repo: ModerationResultRepository = ModerationResultRepository()

    async def enqueue(self, item_id: int, kafka_client: Any) -> tuple[int, str]:
        await self.add_repo.get(item_id)
        moderation_task = await self.moderation_repo.create_pending(item_id)

        if kafka_client is None:
            raise KafkaUnavailableError("Kafka is unavailable")

        try:
            await kafka_client.send_moderation_request(
                item_id=item_id,
                task_id=moderation_task.id,
            )
        except Exception as exc:
            await self.moderation_repo.mark_failed(moderation_task.id, str(exc))
            raise ModerationEnqueueError("Failed to enqueue moderation request") from exc

        return moderation_task.id, moderation_task.status

    async def get_result(self, task_id: int) -> Any:
        return await self.moderation_repo.get(task_id)
