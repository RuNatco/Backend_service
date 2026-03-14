from __future__ import annotations

import asyncio
from types import SimpleNamespace

from fastapi import HTTPException

from errors import AddNotFoundError, ModerationTaskNotFoundError
from routers.async_moderation import (
    AsyncPredictRequest,
    async_predict,
    close_add,
    moderation_result,
)
from routers.predict import PredictRequest, predict, simple_predict
from models.accounts import AccountModel


ACCOUNT = AccountModel(id=1, login="test_login", password="hashed", is_blocked=False)


def test_predict_handler_uses_service_without_db(monkeypatch) -> None:
    async def fake_predict_from_payload(self, *, payload, model, cache_storage):
        assert payload["item_id"] == 77
        return False, 0.1

    monkeypatch.setattr("services.predict.PredictService.predict_from_payload", fake_predict_from_payload)
    req = PredictRequest(
        seller_id=1,
        is_verified_seller=False,
        item_id=77,
        name="item",
        description="desc",
        category=1,
        images_qty=1,
    )
    http_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(model=object(), prediction_cache=None)))

    resp = asyncio.run(predict(req, http_request, ACCOUNT))

    assert resp.is_violation is False
    assert resp.probability == 0.1


def test_simple_predict_handler_returns_404_on_not_found(monkeypatch) -> None:
    async def fake_predict_by_item_id(self, *, item_id, model, cache_storage):
        raise AddNotFoundError()

    monkeypatch.setattr("services.predict.PredictService.predict_by_item_id", fake_predict_by_item_id)
    http_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(model=object(), prediction_cache=None)))

    try:
        asyncio.run(simple_predict(1, http_request, ACCOUNT))
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 404


def test_async_handlers_with_mocked_service(monkeypatch) -> None:
    async def fake_enqueue(self, *, item_id, kafka_client):
        return 5, "pending"

    async def fake_get_result(self, task_id, cache_storage=None):
        return SimpleNamespace(
            id=task_id,
            status="completed",
            is_violation=False,
            probability=0.2,
            error_message=None,
        )

    async def fake_close(self, item_id, cache_storage=None):
        return None

    monkeypatch.setattr("services.moderation.ModerationService.enqueue", fake_enqueue)
    monkeypatch.setattr("services.moderation.ModerationService.get_result", fake_get_result)
    monkeypatch.setattr("services.moderation.ModerationService.close_item", fake_close)

    http_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(kafka_client=object(), prediction_cache=None)))
    enqueue_resp = asyncio.run(async_predict(AsyncPredictRequest(item_id=10), http_request, ACCOUNT))
    result_resp = asyncio.run(moderation_result(5, http_request, ACCOUNT))
    close_resp = asyncio.run(close_add(10, http_request, ACCOUNT))

    assert enqueue_resp.task_id == 5
    assert result_resp.status == "completed"
    assert close_resp.status == "closed"


def test_moderation_result_handler_not_found(monkeypatch) -> None:
    async def fake_get_result(self, task_id, cache_storage=None):
        raise ModerationTaskNotFoundError()

    monkeypatch.setattr("services.moderation.ModerationService.get_result", fake_get_result)
    http_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(prediction_cache=None)))

    try:
        asyncio.run(moderation_result(999, http_request, ACCOUNT))
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 404
