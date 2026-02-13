import asyncio
from http import HTTPStatus
from typing import Any

from fastapi.testclient import TestClient
import pytest

from repositories.adds import AddRepository
from repositories.moderation_results import ModerationResultRepository
from repositories.users import UserRepository
from workers.moderation_worker import process_moderation_message


class _KafkaStub:
    def __init__(self) -> None:
        self.sent_messages: list[dict[str, Any]] = []
        self.sent_dlq: list[dict[str, Any]] = []

    async def send_moderation_request(
        self,
        item_id: int,
        task_id: int,
        retry_count: int = 0,
    ) -> None:
        self.sent_messages.append(
            {"item_id": item_id, "task_id": task_id, "retry_count": retry_count}
        )

    async def send_to_dlq(
        self,
        original_message: dict[str, Any],
        error: str,
        retry_count: int = 1,
    ) -> None:
        self.sent_dlq.append(
            {
                "original_message": original_message,
                "error": error,
                "retry_count": retry_count,
            }
        )


def _create_user_and_add() -> tuple[int, int]:
    user_repo = UserRepository()
    add_repo = AddRepository()
    user = asyncio.run(
        user_repo.create(
            name="Async User",
            password="pass",
            email="async@example.com",
            is_verified_seller=False,
        )
    )
    add = asyncio.run(
        add_repo.create(
            seller_id=user.id,
            name="Async Add",
            description="Need moderation",
            category=10,
            images_qty=0,
        )
    )
    return user.id, add.id


def test_async_predict_creates_task(
    app_client: TestClient,
) -> None:
    _, add_id = _create_user_and_add()
    kafka_stub = _KafkaStub()
    app_client.app.state.kafka_client = kafka_stub

    response = app_client.post("/async_predict", json={"item_id": add_id})

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["status"] == "pending"
    assert data["task_id"] > 0
    assert kafka_stub.sent_messages


def test_moderation_result_endpoint(
    app_client: TestClient,
) -> None:
    _, add_id = _create_user_and_add()
    repo = ModerationResultRepository()
    task = asyncio.run(repo.create_pending(add_id))

    response = app_client.get(f"/moderation_result/{task.id}")

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["task_id"] == task.id
    assert data["status"] == "pending"
    assert data["is_violation"] is None
    assert data["probability"] is None


def test_worker_processes_message(
    clean_db: None,
) -> None:
    _, add_id = _create_user_and_add()
    repo = ModerationResultRepository()
    task = asyncio.run(repo.create_pending(add_id))
    kafka_stub = _KafkaStub()

    class _ModelStub:
        def predict_proba(self, *_: Any, **__: Any) -> list[list[float]]:
            return [[0.3, 0.7]]

        def predict(self, *_: Any, **__: Any) -> list[bool]:
            return [True]

    asyncio.run(
        process_moderation_message(
            payload={"item_id": add_id, "task_id": task.id},
            model=_ModelStub(),
            moderation_repo=repo,
            add_repo=AddRepository(),
            user_repo=UserRepository(),
            kafka_client=kafka_stub,
        )
    )

    updated = asyncio.run(repo.get(task.id))
    assert updated.status == "completed"
    assert updated.is_violation is True
    assert updated.probability == 0.7


def test_worker_sends_to_dlq_on_error(clean_db: None) -> None:
    repo = ModerationResultRepository()
    _, add_id = _create_user_and_add()
    task = asyncio.run(repo.create_pending(add_id))
    kafka_stub = _KafkaStub()

    class _ModelStub:
        def predict_proba(self, *_: Any, **__: Any) -> list[list[float]]:
            return [[0.5, 0.5]]

        def predict(self, *_: Any, **__: Any) -> list[bool]:
            return [False]

    asyncio.run(
        process_moderation_message(
            payload={"item_id": 42424242, "task_id": task.id},
            model=_ModelStub(),
            moderation_repo=repo,
            add_repo=AddRepository(),
            user_repo=UserRepository(),
            kafka_client=kafka_stub,
        )
    )

    updated = asyncio.run(repo.get(task.id))
    assert updated.status == "failed"
    assert kafka_stub.sent_dlq


def test_worker_retries_temporary_error(clean_db: None) -> None:
    _, add_id = _create_user_and_add()
    repo = ModerationResultRepository()
    task = asyncio.run(repo.create_pending(add_id))
    kafka_stub = _KafkaStub()

    class _ModelStub:
        def predict_proba(self, *_: Any, **__: Any) -> list[list[float]]:
            raise RuntimeError("temporary model error")

        def predict(self, *_: Any, **__: Any) -> list[bool]:
            return [False]

    asyncio.run(
        process_moderation_message(
            payload={"item_id": add_id, "task_id": task.id, "retry_count": 0},
            model=_ModelStub(),
            moderation_repo=repo,
            add_repo=AddRepository(),
            user_repo=UserRepository(),
            kafka_client=kafka_stub,
        )
    )

    current = asyncio.run(repo.get(task.id))
    assert current.status == "pending"
    assert current.error_message == "temporary model error"
    assert len(kafka_stub.sent_messages) == 1
    assert kafka_stub.sent_messages[0]["retry_count"] == 1
    assert not kafka_stub.sent_dlq
