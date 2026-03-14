import asyncio
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest

from errors import AccountBlockedError, AccountNotFoundError, InvalidCredentialsError, UnauthorizedError
from models.accounts import AccountModel
from services.auth import AuthService, JWT_ALGORITHM, JWT_SECRET


ACCOUNT = AccountModel(id=7, login="acc", password="hashed", is_blocked=False)


def test_authenticate_success() -> None:
    repo = MagicMock()
    repo.get_by_login_and_password = AsyncMock(return_value=ACCOUNT)

    service = AuthService(account_repo=repo)
    result = asyncio.run(service.authenticate("acc", "secret"))

    assert result.id == ACCOUNT.id


def test_authenticate_invalid_credentials() -> None:
    repo = MagicMock()
    repo.get_by_login_and_password = AsyncMock(side_effect=AccountNotFoundError())

    service = AuthService(account_repo=repo)

    with pytest.raises(InvalidCredentialsError):
        asyncio.run(service.authenticate("acc", "secret"))


def test_authenticate_blocked_account() -> None:
    repo = MagicMock()
    repo.get_by_login_and_password = AsyncMock(
        return_value=AccountModel(id=1, login="blocked", password="hashed", is_blocked=True)
    )

    service = AuthService(account_repo=repo)

    with pytest.raises(AccountBlockedError):
        asyncio.run(service.authenticate("blocked", "secret"))


def test_create_and_verify_access_token() -> None:
    repo = MagicMock()
    repo.get = AsyncMock(return_value=ACCOUNT)
    service = AuthService(account_repo=repo)

    token = service.create_access_token(ACCOUNT)
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    account = asyncio.run(service.get_account_by_token(token))

    assert payload["sub"] == str(ACCOUNT.id)
    assert account.id == ACCOUNT.id


def test_get_account_by_invalid_token() -> None:
    service = AuthService(account_repo=MagicMock())

    with pytest.raises(UnauthorizedError):
        asyncio.run(service.get_account_by_token("bad-token"))
