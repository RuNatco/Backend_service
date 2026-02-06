from typing import Mapping, Tuple
import asyncio
from http import HTTPStatus
import pytest
from fastapi.testclient import TestClient
from repositories.users import UserRepository
from repositories.adds import AddRepository


@pytest.fixture
def base_payload() -> Mapping[str, object]:
    return {
        'seller_id': 1,
        'is_verified_seller': False,
        'item_id': 100,
        'name': 'Sample item',
        'description': 'Sample description',
        'category': 10,
        'images_qty': 1,
    }


def create_user_and_add(
    *,
    is_verified_seller: bool,
    images_qty: int,
) -> Tuple[int, int]:
    user_repo = UserRepository()
    add_repo = AddRepository()

    user = asyncio.run(
        user_repo.create(
            name="Seller",
            password="secret",
            email="seller@example.com",
            is_verified_seller=is_verified_seller,
        )
    )
    add = asyncio.run(
        add_repo.create(
            seller_id=user.id,
            name="Item",
            description="Desc",
            category=10,
            images_qty=images_qty,
        )
    )
    return user.id, add.id


@pytest.mark.parametrize(
    "overrides,expected_violation",
    [
        ({'is_verified_seller': False, 'images_qty': 0}, True),
        ({'is_verified_seller': True, 'images_qty': 10}, False),
    ],
)
def test_predict(
    app_client: TestClient,
    base_payload: Mapping[str, object],
    overrides: Mapping[str, object],
    expected_violation: bool,
) -> None:
    payload = {**base_payload, **overrides}

    response = app_client.post('/predict', json=payload)

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['is_violation'] is expected_violation
    assert 0.0 <= data['probability'] <= 1.0


def test_validation_error(
    app_client: TestClient,
    base_payload: Mapping[str, object],
) -> None:
    payload = {**base_payload, 'seller_id': 'wrong-type'}

    response = app_client.post('/predict', json=payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_model_unavailable(
    app_client: TestClient,
    base_payload: Mapping[str, object],
) -> None:
    app = app_client.app
    original_model = getattr(app.state, "model", None)
    app.state.model = None
    try:
        response = app_client.post('/predict', json=base_payload)
    finally:
        app.state.model = original_model

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json()['detail'] == 'Model is not loaded'


def test_prediction_error_returns_500(
    app_client: TestClient,
    base_payload: Mapping[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(*_: object, **__: object) -> tuple[bool, float]:
        raise RuntimeError("boom")

    monkeypatch.setattr("routers.predict.predict_violation", explode)

    response = app_client.post('/predict', json=base_payload)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()['detail'] == 'Prediction failed'


@pytest.mark.parametrize(
    "is_verified_seller,images_qty,expected_violation",
    [
        (False, 0, True),
        (True, 10, False),
    ],
)
def test_simple_predict(
    app_client: TestClient,
    is_verified_seller: bool,
    images_qty: int,
    expected_violation: bool,
) -> None:
    _, add_id = create_user_and_add(
        is_verified_seller=is_verified_seller,
        images_qty=images_qty,
    )

    response = app_client.get(f"/predict/simple_predict?item_id={add_id}")

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["is_violation"] is expected_violation
    assert 0.0 <= data["probability"] <= 1.0


def test_repositories_create_user_and_add() -> None:
    user_repo = UserRepository()
    add_repo = AddRepository()

    user = asyncio.run(
        user_repo.create(
            name="Repo User",
            password="pass",
            email="repo@example.com",
            is_verified_seller=False,
        )
    )
    add = asyncio.run(
        add_repo.create(
            seller_id=user.id,
            name="Repo Item",
            description="Repo Desc",
            category=5,
            images_qty=2,
        )
    )

    assert user.id
    assert add.id
    assert add.seller_id == user.id

