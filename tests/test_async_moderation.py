import asyncio
from http import HTTPStatus
from typing import Any, Callable

from fastapi.testclient import TestClient
import pytest

from errors import AddNotFoundError, ModerationTaskNotFoundError
from repositories.adds import AddRepository
from repositories.moderation_results import ModerationResultRepository
from repositories.users import UserRepository
from workers.moderation_worker import process_moderation_message

pytestmark = pytest.mark.integration


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


def test_async_predict_creates_task(
    authorized_app_client: TestClient,
    create_user_and_add: Callable[[bool, int], tuple[int, int]],
) -> None:
    _, add_id = create_user_and_add(False, 0)
    kafka_stub = _KafkaStub()
    authorized_app_client.app.state.kafka_client = kafka_stub

    response = authorized_app_client.post("/async_predict", json={"item_id": add_id})

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["status"] == "pending"
    assert data["task_id"] > 0
    assert kafka_stub.sent_messages


def test_async_predict_returns_404_for_missing_add(
    authorized_app_client: TestClient,
) -> None:
    kafka_stub = _KafkaStub()
    authorized_app_client.app.state.kafka_client = kafka_stub

    response = authorized_app_client.post("/async_predict", json={"item_id": 999999})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"] == "Add not found"


def test_async_predict_returns_503_without_kafka(
    authorized_app_client: TestClient,
    create_user_and_add: Callable[[bool, int], tuple[int, int]],
) -> None:
    _, add_id = create_user_and_add(False, 0)
    authorized_app_client.app.state.kafka_client = None

    response = authorized_app_client.post("/async_predict", json={"item_id": add_id})

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json()["detail"] == "Kafka is unavailable"


def test_moderation_result_endpoint(
    authorized_app_client: TestClient,
    create_user_and_add: Callable[[bool, int], tuple[int, int]],
) -> None:
    _, add_id = create_user_and_add(False, 0)
    repo = ModerationResultRepository()
    task = asyncio.run(repo.create_pending(add_id))

    response = authorized_app_client.get(f"/moderation_result/{task.id}")

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["task_id"] == task.id
    assert data["status"] == "pending"
    assert data["is_violation"] is None
    assert data["probability"] is None


def test_moderation_result_endpoint_returns_404_for_missing_task(
    authorized_app_client: TestClient,
) -> None:
    response = authorized_app_client.get("/moderation_result/999999")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"] == "Task not found"


def test_close_add_removes_add_and_results(
    authorized_app_client: TestClient,
    create_user_and_add: Callable[[bool, int], tuple[int, int]],
) -> None:
    _, add_id = create_user_and_add(False, 0)
    moderation_repo = ModerationResultRepository()
    add_repo = AddRepository()
    task = asyncio.run(moderation_repo.create_pending(add_id))

    response = authorized_app_client.post(f"/close?item_id={add_id}")

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["item_id"] == add_id
    assert body["status"] == "closed"

    with pytest.raises(AddNotFoundError):
        asyncio.run(add_repo.get(add_id))
    with pytest.raises(ModerationTaskNotFoundError):
        asyncio.run(moderation_repo.get(task.id))


def test_async_predict_requires_authentication(app_client: TestClient) -> None:
    response = app_client.post("/async_predict", json={"item_id": 1})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_worker_processes_message(
    clean_db: None,
    create_user_and_add: Callable[[bool, int], tuple[int, int]],
) -> None:
    _, add_id = create_user_and_add(False, 0)
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


def test_worker_sends_to_dlq_on_error(
    clean_db: None,
    create_user_and_add: Callable[[bool, int], tuple[int, int]],
) -> None:
    repo = ModerationResultRepository()
    _, add_id = create_user_and_add(False, 0)
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


def test_worker_retries_temporary_error(
    clean_db: None,
    create_user_and_add: Callable[[bool, int], tuple[int, int]],
) -> None:
    _, add_id = create_user_and_add(False, 0)
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
