from fastapi import APIRouter, HTTPException, status, Response, Request
from typing import Sequence
from pydantic import BaseModel
from models.accounts import AccountPublicModel
from models.users import UserModel
from errors import AccountBlockedError, InvalidCredentialsError
from services.auth import AUTH_COOKIE_NAME, AuthService
from services.users import UserService
from errors import UserNotFoundError


class CreateUserInDto(BaseModel):
    name: str
    password: str
    email: str


class LoginAccountInDto(BaseModel):
    login: str
    password: str



router = APIRouter()
root_router = APIRouter()

user_service = UserService()
auth_service = AuthService()


@router.get('/', status_code=status.HTTP_200_OK)
async def get_many() -> Sequence[UserModel]:
    return await user_service.get_many()


@router.post('/', status_code=status.HTTP_201_CREATED)
async def register(data: CreateUserInDto) -> UserModel:
    return await user_service.register(dict(data))


@router.get('/{user_id}')
async def get(user_id: str) -> UserModel:
    try:
        return await user_service.get(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Пользователь {user_id} не найден',
        )

@router.get('/current/')
async def get_current(request: Request) -> UserModel:
    user_id = request.cookies.get('x-user-id')

    try:
        return await user_service.get(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Пользователь {user_id} не найден',
        )


@router.patch('/deactivate/{user_id}')
async def deactivate(user_id: str, request: Request) -> UserModel:
    user_id = request.cookies.get('x-user-id')

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )

    return await user_service.deactivate(user_id)


@router.delete('/{user_id}')
async def delete(user_id: str, request: Request) -> UserModel:
    user_id = request.cookies.get('x-user-id')

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Unauthorized',
        )

    try:
        return await user_service.delete(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Пользователь {user_id} не найден',
        )


@root_router.post('/login')
async def login(
    dto: LoginAccountInDto,
    response: Response,
) -> AccountPublicModel:
    try:
        account = await auth_service.authenticate(dto.login, dto.password)
        token = auth_service.create_access_token(account)

        response.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
        )

        return AccountPublicModel(
            id=account.id,
            login=account.login,
            is_blocked=account.is_blocked,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid login or password',
        )
    except AccountBlockedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Account is blocked',
        )
