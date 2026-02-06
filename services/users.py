from dataclasses import dataclass
from models.users import UserModel
from typing import Mapping
from typing import Sequence
from typing import Any
from typing import Union
from repositories.users import UserRepository


@dataclass(frozen=True)
class UserService:
    user_repo: UserRepository = UserRepository()

    async def register(self, values: Mapping[str, Any]) -> UserModel:
        return await self.user_repo.create(**values)


    async def login(self, name: str, password: str) -> UserModel:
        user = await self.user_repo.get_by_name_and_password(name, password)

        if not user:
            raise ValueError("Incorrect name or password")
        
        return user
    

    async def get(self, user_id: Union[str, int]) -> UserModel:
        return await self.user_repo.get(int(user_id))


    async def delete(self, user_id: Union[str, int]) -> UserModel:
        return await self.user_repo.delete(int(user_id))


    async def deactivate(self, user_id: Union[str, int]) -> UserModel:
        return await self.user_repo.update(int(user_id), is_active=False)
    

    async def get_many(self) -> Sequence[UserModel]:
        return await self.user_repo.get_many()
