from __future__ import annotations

from fastapi import HTTPException, Request, status

from errors import AccountBlockedError, AccountNotFoundError, UnauthorizedError
from models.accounts import AccountModel
from services.auth import AUTH_COOKIE_NAME, AuthService

auth_service = AuthService()


async def get_current_account(request: Request) -> AccountModel:
    token = request.cookies.get(AUTH_COOKIE_NAME, "")

    try:
        return await auth_service.get_account_by_token(token)
    except AccountBlockedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (UnauthorizedError, AccountNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized") from exc
