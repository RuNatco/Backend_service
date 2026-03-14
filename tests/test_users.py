from typing import Any, Mapping, Generator
import asyncio
import pytest
from fastapi.testclient import TestClient
from main import app
from http import HTTPStatus
from repositories.accounts import AccountRepository

pytestmark = pytest.mark.integration

PASSWORD = 'qwerty'


@pytest.mark.parametrize('name', ['Иванов И.И.'])
@pytest.mark.parametrize('password', [PASSWORD])
def test_create_user(
    some_user: Mapping[str, Any],
    app_client: TestClient
):
    assert some_user['name'] == 'Иванов И.И.'
    assert some_user['id']

    read_response = app_client.get(f'/users/{some_user["id"]}')
    read_user = read_response.json()

    assert read_response.status_code == HTTPStatus.OK
    assert read_user['id'] == some_user['id']
    assert read_user['name'] == some_user['name']


@pytest.mark.parametrize('name', ['Иванов И.И.'])
@pytest.mark.parametrize('password', [PASSWORD])
def test_deactivate_user(
    app_client: TestClient,
    some_user: Mapping[str, Any]
):
    app_client.cookies.set('x-user-id', str(some_user['id']))
    update_response = app_client.patch(f'/users/deactivate/{some_user["id"]}')
    app_client.cookies.clear()
    assert update_response.status_code == HTTPStatus.OK, update_response.json()

    updated_user = update_response.json()
    assert updated_user['id'] == some_user['id']
    assert not updated_user['is_active']


@pytest.mark.parametrize('name', ['Иванов И.И.'])
@pytest.mark.parametrize('password', [PASSWORD])
def test_delete_user(
    app_client: TestClient,
    some_user: Mapping[str, Any]
):
    app_client.cookies.set('x-user-id', str(some_user['id']))
    delete_response = app_client.delete(f'/users/{some_user["id"]}')
    app_client.cookies.clear()
    assert delete_response.status_code == HTTPStatus.OK, delete_response.json()

    deleted_user = delete_response.json()
    assert deleted_user['id'] == some_user['id']

    get_user = app_client.get(f'/users/{deleted_user["id"]}')
    assert get_user.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize('name', ['Иванов И.И.'])
@pytest.mark.parametrize('password', [PASSWORD])
def test_get_many_users(
    app_client: TestClient,
    some_user: Mapping[str, Any]
):
    get_users_response = app_client.get(f'/users')
    assert get_users_response.status_code == HTTPStatus.OK

    users = get_users_response.json()
    assert len(users) == 1

    app_client.cookies.set('x-user-id', str(some_user['id']))
    delete_response = app_client.delete(f'/users/{some_user["id"]}')
    app_client.cookies.clear()
    assert delete_response.status_code == HTTPStatus.OK, delete_response.json()

    get_users_response = app_client.get(f'/users')
    assert get_users_response.status_code == HTTPStatus.OK

    users = get_users_response.json()
    assert len(users) == 0


def test_login_user(
    app_client: TestClient,
    clean_db: None,
):
    account = asyncio.run(AccountRepository().create(login="login_user", password=PASSWORD))
    login_response = app_client.post(f'/login', json=dict(
        login="login_user",
        password=PASSWORD,
    ))
    assert login_response.status_code == HTTPStatus.OK, login_response.json()
    assert login_response.cookies.get('access_token')

    logged_user = login_response.json()
    assert logged_user['id'] == account.id
    assert logged_user['login'] == account.login


@pytest.mark.parametrize('name', ['Иванов И.И.'])
@pytest.mark.parametrize('password', [PASSWORD])
def test_get_current_user(
    app_client: TestClient,
    some_user: Mapping[str, Any]
):
    app_client.cookies.set('x-user-id', str(some_user['id']))
    get_response = app_client.get('/users/current/')
    app_client.cookies.clear()
    assert get_response.status_code == HTTPStatus.OK

    get_user = get_response.json()
    assert get_user['id'] == some_user['id']
