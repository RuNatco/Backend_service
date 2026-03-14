import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from dependencies.auth import get_current_account
from errors import AccountBlockedError, UnauthorizedError
from models.accounts import AccountModel


ACCOUNT = AccountModel(id=1, login="acc", password="hashed", is_blocked=False)


def test_get_current_account_returns_account(monkeypatch) -> None:
    async def fake_get_account_by_token(token: str) -> AccountModel:
        assert token == "token"
        return ACCOUNT

    monkeypatch.setattr(
        "dependencies.auth.auth_service",
        SimpleNamespace(get_account_by_token=fake_get_account_by_token),
    )
    request = SimpleNamespace(cookies={"access_token": "token"})

    result = asyncio.run(get_current_account(request))

    assert result.id == ACCOUNT.id


def test_get_current_account_unauthorized(monkeypatch) -> None:
    async def fake_get_account_by_token(token: str) -> AccountModel:
        raise UnauthorizedError("bad token")

    monkeypatch.setattr(
        "dependencies.auth.auth_service",
        SimpleNamespace(get_account_by_token=fake_get_account_by_token),
    )
    request = SimpleNamespace(cookies={})

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_account(request))

    assert exc_info.value.status_code == 401


def test_get_current_account_blocked(monkeypatch) -> None:
    async def fake_get_account_by_token(token: str) -> AccountModel:
        raise AccountBlockedError("Account is blocked")

    monkeypatch.setattr(
        "dependencies.auth.auth_service",
        SimpleNamespace(get_account_by_token=fake_get_account_by_token),
    )
    request = SimpleNamespace(cookies={"access_token": "token"})

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_account(request))

    assert exc_info.value.status_code == 403
