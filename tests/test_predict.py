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
    payload = {**base_payload, 'is_verified_seller': False, 'images_qty': 0}

    response = app_client.post('/predict', json=payload)

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['is_violation'] is True
    assert 0.0 <= data['probability'] <= 1.0


def test_predict_unverified(
    app_client: TestClient,
    base_payload: Mapping[str, object],
) -> None:
    payload = {**base_payload, 'is_verified_seller': True, 'images_qty': 10}

    response = app_client.post('/predict', json=payload)

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['is_violation'] is False
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

