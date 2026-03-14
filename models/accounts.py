from pydantic import BaseModel


class AccountModel(BaseModel):
    id: int
    login: str
    password: str
    is_blocked: bool = False


class AccountPublicModel(BaseModel):
    id: int
    login: str
    is_blocked: bool = False
