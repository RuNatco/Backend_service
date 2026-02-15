from typing import Any, Mapping, Generator, Callable
import os
import sys
from pathlib import Path
import asyncio
import pytest
from fastapi.testclient import TestClient
from http import HTTPStatus

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
os.environ["DISABLE_KAFKA"] = "true"

from main import app
from models.model import train_and_save_model
from db.connection import DB_DSN, get_connection
from db.migrate import apply_migrations
from repositories.users import UserRepository
from repositories.adds import AddRepository

MODEL_PATH = Path(ROOT_DIR) / "model.pkl"
MIGRATIONS_DIR = Path(ROOT_DIR) / "db"


@pytest.fixture(scope="session")
def model_file() -> Path:
    if not MODEL_PATH.exists():
        train_and_save_model(MODEL_PATH)
    return MODEL_PATH


@pytest.fixture(scope="session")
def migrated_db() -> None:
    apply_migrations(MIGRATIONS_DIR, DB_DSN)


@pytest.fixture(scope="function", autouse=True)
def clean_db(migrated_db: None) -> None:
    with get_connection(DB_DSN) as conn:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE moderation_results RESTART IDENTITY CASCADE")
            cursor.execute("TRUNCATE TABLE adds RESTART IDENTITY CASCADE")
            cursor.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE")
        conn.commit()


@pytest.fixture
def app_client(model_file: Path, clean_db: None) -> Generator[TestClient, None, None]:
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


@pytest.fixture(scope="function")
def create_user_and_add() -> Callable[[bool, int], tuple[int, int]]:
    def _create(is_verified_seller: bool, images_qty: int) -> tuple[int, int]:
        user = asyncio.run(
            UserRepository().create(
                name="Fixture User",
                password="secret",
                email="fixture_user@example.com",
                is_verified_seller=is_verified_seller,
            )
        )
        add = asyncio.run(
            AddRepository().create(
                seller_id=user.id,
                name="Fixture Add",
                description="Fixture description",
                category=10,
                images_qty=images_qty,
            )
        )
        return user.id, add.id

    return _create
