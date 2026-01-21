from typing import Any, Mapping, Generator
import os
import sys
import pytest
from fastapi.testclient import TestClient
from http import HTTPStatus

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import app


@pytest.fixture
def app_client() -> Generator[TestClient, None, None]:
    return TestClient(app)


@pytest.fixture(scope='function')
def some_user(
    app_client: TestClient,
    name: str,
    password: str,
) -> Generator[Mapping[str, Any], None, None]:
    create_response = app_client.post('/users', json=dict(
        name=name,
        password=password,
        email=f'{name.lower().replace(".", "_").replace(" ", "_")}@example.com'
    ))
    created_user = create_response.json()

    assert create_response.status_code == HTTPStatus.CREATED
    yield created_user

    deleted_response = app_client.delete(
        f'/users/{created_user["id"]}',
        cookies={
            'x-user-id': str(created_user['id'])
        },
    )
    assert deleted_response.status_code == HTTPStatus.OK or deleted_response.status_code == HTTPStatus.NOT_FOUND