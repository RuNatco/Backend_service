import json
import os
from typing import Any
from aiokafka import AIOKafkaConsumer
from clients.kafka import KafkaClient, KAFKA_BOOTSTRAP_SERVERS, MODERATION_TOPIC
from models.model import load_model
from repositories.adds import AddRepository
from repositories.moderation_results import ModerationResultRepository
from repositories.users import UserRepository
from services.moderation_processing import process_moderation_message


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
    import asyncio

    asyncio.run(run_worker())
