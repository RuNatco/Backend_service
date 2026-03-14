import asyncio
from types import SimpleNamespace

from fastapi import Response

from models.accounts import AccountModel
from routers.users import LoginAccountInDto, login


ACCOUNT = AccountModel(id=1, login="acc", password="hashed", is_blocked=False)


def test_login_handler_sets_cookie(monkeypatch) -> None:
    async def fake_authenticate(login_value: str, password: str) -> AccountModel:
        assert login_value == "acc"
        assert password == "secret"
        return ACCOUNT

    def fake_create_access_token(account: AccountModel) -> str:
        assert account.id == ACCOUNT.id
        return "jwt-token"

    monkeypatch.setattr(
        "routers.users.auth_service",
        SimpleNamespace(
            authenticate=fake_authenticate,
            create_access_token=fake_create_access_token,
        ),
    )

    response = Response()
    result = asyncio.run(login(LoginAccountInDto(login="acc", password="secret"), response))

    assert result.id == ACCOUNT.id
    assert result.login == ACCOUNT.login
    assert "access_token=jwt-token" in response.headers["set-cookie"]
