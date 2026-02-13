import json
from datetime import datetime, timezone
import os
from typing import Any, Optional
from aiokafka import AIOKafkaProducer


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
MODERATION_TOPIC = os.getenv("KAFKA_MODERATION_TOPIC", "moderation")
MODERATION_DLQ_TOPIC = os.getenv("KAFKA_MODERATION_DLQ_TOPIC", "moderation_dlq")


class KafkaClient:
    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS) -> None:
        self.bootstrap_servers = bootstrap_servers
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        if self._producer is None:
            self._producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
            await self._producer.start()

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def send_moderation_request(
        self,
        item_id: int,
        task_id: int,
        retry_count: int = 0,
    ) -> None:
        await self._send_json(
            MODERATION_TOPIC,
            {
                "item_id": item_id,
                "task_id": task_id,
                "retry_count": retry_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def send_to_dlq(
        self,
        original_message: dict[str, Any],
        error: str,
        retry_count: int = 1,
    ) -> None:
        await self._send_json(
            MODERATION_DLQ_TOPIC,
            {
                "original_message": original_message,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "retry_count": retry_count,
            },
        )

    async def _send_json(self, topic: str, payload: dict[str, Any]) -> None:
        if self._producer is None:
            raise RuntimeError("Kafka producer is not started")
        await self._producer.send_and_wait(topic, json.dumps(payload).encode("utf-8"))
