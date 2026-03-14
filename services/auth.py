from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from errors import AccountBlockedError, AccountNotFoundError, InvalidCredentialsError, UnauthorizedError
from models.accounts import AccountModel
from repositories.accounts import AccountRepository

AUTH_COOKIE_NAME = "access_token"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-jwt-secret-change-me-1234567890")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "60"))


@dataclass(frozen=True)
class AuthService:
    account_repo: AccountRepository = AccountRepository()

    async def authenticate(self, login: str, password: str) -> AccountModel:
        try:
            account = await self.account_repo.get_by_login_and_password(login, password)
        except AccountNotFoundError as exc:
            raise InvalidCredentialsError("Invalid login or password") from exc

        if account.is_blocked:
            raise AccountBlockedError("Account is blocked")
        return account

    def create_access_token(self, account: AccountModel) -> str:
        payload = {
            "sub": str(account.id),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRES_MINUTES),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    async def get_account_by_token(self, token: str) -> AccountModel:
        if not token:
            raise UnauthorizedError("Missing access token")

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except InvalidTokenError as exc:
            raise UnauthorizedError("Invalid access token") from exc

        account_id = payload.get("sub")
        if account_id is None:
            raise UnauthorizedError("Invalid access token")

        account = await self.account_repo.get(int(account_id))
        if account.is_blocked:
            raise AccountBlockedError("Account is blocked")
        return account
