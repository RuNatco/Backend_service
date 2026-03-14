import asyncio

import pytest

from errors import AccountNotFoundError
from repositories.accounts import AccountRepository, hash_password

pytestmark = pytest.mark.integration


def test_account_repository_flow(clean_db: None) -> None:
    repo = AccountRepository()

    account = asyncio.run(repo.create(login="acc_login", password="secret"))
    loaded = asyncio.run(repo.get(account.id))
    authorized = asyncio.run(repo.get_by_login_and_password("acc_login", "secret"))
    blocked = asyncio.run(repo.block(account.id))
    deleted = asyncio.run(repo.delete(account.id))

    assert loaded.login == "acc_login"
    assert loaded.password == hash_password("secret")
    assert authorized.id == account.id
    assert blocked.is_blocked is True
    assert deleted.id == account.id

    with pytest.raises(AccountNotFoundError):
        asyncio.run(repo.get(account.id))
