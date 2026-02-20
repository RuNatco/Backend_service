from dataclasses import dataclass
from typing import Any, Optional

from errors import (
    KafkaUnavailableError,
    ModerationEnqueueError,
)
from models.moderation_results import ModerationResultModel
from repositories.adds import AddRepository
from repositories.moderation_results import ModerationResultRepository
from storages.prediction_cache import PredictionCacheStorage


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

    async def get_result(
        self,
        task_id: int,
        cache_storage: Optional[PredictionCacheStorage] = None,
    ) -> ModerationResultModel:
        if cache_storage is not None:
            cached = await cache_storage.get_moderation_result(task_id)
            if cached is not None:
                return ModerationResultModel(**cached)

        result = await self.moderation_repo.get(task_id)
        if cache_storage is not None:
            await cache_storage.set_moderation_result(task_id, result.dict())
        return result

    async def close_item(
        self,
        item_id: int,
        cache_storage: Optional[PredictionCacheStorage] = None,
    ) -> None:
        task_ids = await self.moderation_repo.get_task_ids_by_item_id(item_id)
        await self.moderation_repo.delete_by_item_id(item_id)
        await self.add_repo.delete(item_id)

        if cache_storage is not None:
            await cache_storage.delete_item_predictions(item_id)
            for task_id in task_ids:
                await cache_storage.delete_moderation_result(task_id)
