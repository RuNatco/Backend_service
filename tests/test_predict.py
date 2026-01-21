from typing import Mapping
from http import HTTPStatus
import pytest
from fastapi.testclient import TestClient


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


def test_predict_verified(
    app_client: TestClient,
    base_payload: Mapping[str, object],
) -> None:
    payload = {**base_payload, 'is_verified_seller': True, 'images_qty': 0}

    response = app_client.post('/predict', json=payload)

    assert response.status_code == HTTPStatus.OK
    assert response.json() is True


def test_predict_unverified(
    app_client: TestClient,
    base_payload: Mapping[str, object],
) -> None:
    payload = {**base_payload, 'is_verified_seller': False, 'images_qty': 0}

    response = app_client.post('/predict', json=payload)

    assert response.status_code == HTTPStatus.OK
    assert response.json() is False


def test_validation_error(
    app_client: TestClient,
    base_payload: Mapping[str, object],
) -> None:
    payload = dict(base_payload)
    payload.pop('name')

    response = app_client.post('/predict', json=payload)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_business_logic(
    app_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    base_payload: Mapping[str, object],
) -> None:
    def explode(*_: object, **__: object) -> bool:
        raise RuntimeError('unexpected failure')

    monkeypatch.setattr('routers.predict.apply_prediction_rules', explode)

    response = app_client.post('/predict', json=base_payload)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()['detail'] == 'Prediction failed'

