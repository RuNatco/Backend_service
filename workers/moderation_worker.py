import asyncio
import json
import os
from typing import Any
from aiokafka import AIOKafkaConsumer
from clients.kafka import KafkaClient, KAFKA_BOOTSTRAP_SERVERS, MODERATION_TOPIC
from errors import AddNotFoundError, UserNotFoundError
from models.model import load_model
from repositories.adds import AddRepository
from repositories.moderation_results import ModerationResultRepository
from repositories.users import UserRepository
from services.predict import predict_violation

MAX_RETRY_COUNT = int(os.getenv("MODERATION_MAX_RETRY_COUNT", "3"))
RETRY_DELAY_SECONDS = float(os.getenv("MODERATION_RETRY_DELAY_SECONDS", "1"))
TEMPORARY_ERRORS = (RuntimeError, ConnectionError, TimeoutError)


async def process_moderation_message(
    payload: dict[str, Any],
    model: Any,
    moderation_repo: ModerationResultRepository,
    add_repo: AddRepository,
    user_repo: UserRepository,
    kafka_client: KafkaClient,
) -> None:
    task_id = int(payload["task_id"])
    item_id = int(payload["item_id"])
    retry_count = int(payload.get("retry_count", 0))
    try:
        add = await add_repo.get(item_id)
        user = await user_repo.get(add.seller_id)
        is_violation, probability = predict_violation(
            model=model,
            seller_id=user.id,
            item_id=add.id,
            is_verified_seller=user.is_verified_seller,
            images_qty=add.images_qty,
            description=add.description,
            category=add.category,
        )
        await moderation_repo.mark_completed(task_id, is_violation, probability)
    except Exception as exc:
        is_temporary = isinstance(exc, TEMPORARY_ERRORS)
        if is_temporary and retry_count < MAX_RETRY_COUNT:
            await moderation_repo.mark_retry(task_id, str(exc))
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            await kafka_client.send_moderation_request(
                item_id=item_id,
                task_id=task_id,
                retry_count=retry_count + 1,
            )
            return

        await moderation_repo.mark_failed(task_id, str(exc))
        await kafka_client.send_to_dlq(
            payload,
            str(exc),
            retry_count=retry_count + 1,
        )


async def run_worker() -> None:
    model_path = os.getenv("MODEL_PATH", os.path.join(os.path.dirname(__file__), "..", "model.pkl"))
    model = load_model(model_path)

    consumer = AIOKafkaConsumer(
        MODERATION_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        group_id="moderation-worker-group",
        auto_offset_reset="earliest",
    )

    kafka_client = KafkaClient(KAFKA_BOOTSTRAP_SERVERS)
    moderation_repo = ModerationResultRepository()
    add_repo = AddRepository()
    user_repo = UserRepository()

    await kafka_client.start()
    await consumer.start()
    try:
        async for message in consumer:
            await process_moderation_message(
                payload=message.value,
                model=model,
                moderation_repo=moderation_repo,
                add_repo=add_repo,
                user_repo=user_repo,
                kafka_client=kafka_client,
            )
    finally:
        await consumer.stop()
        await kafka_client.stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
