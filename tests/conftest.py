from typing import Any, Mapping, Generator
import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from http import HTTPStatus

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import app
from models.model import train_and_save_model
from db.connection import DB_PATH
from db.migrate import apply_migrations

MODEL_PATH = Path(ROOT_DIR) / "model.pkl"
MIGRATIONS_DIR = Path(ROOT_DIR) / "db" / "migrations"


@pytest.fixture(scope="session")
def model_file() -> Path:
    if not MODEL_PATH.exists():
        train_and_save_model(MODEL_PATH)
    return MODEL_PATH


@pytest.fixture(scope="function")
def migrated_db() -> Path:
    if DB_PATH.exists():
        DB_PATH.unlink()
    apply_migrations(DB_PATH, MIGRATIONS_DIR)
    return DB_PATH


@pytest.fixture
def app_client(model_file: Path, migrated_db: Path) -> Generator[TestClient, None, None]:
    with TestClient(app) as client:
        yield client


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

    app_client.cookies.set('x-user-id', str(created_user['id']))
    deleted_response = app_client.delete(f'/users/{created_user["id"]}')
    app_client.cookies.clear()
    assert deleted_response.status_code == HTTPStatus.OK or deleted_response.status_code == HTTPStatus.NOT_FOUND
