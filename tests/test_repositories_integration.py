from __future__ import annotations

import asyncio
import pytest
from errors import AddNotFoundError
from repositories.adds import AddRepository
from repositories.moderation_results import ModerationResultRepository
from repositories.users import UserRepository

pytestmark = pytest.mark.integration


def test_user_add_moderation_flow(clean_db: None) -> None:
    user_repo = UserRepository()
    add_repo = AddRepository()
    moderation_repo = ModerationResultRepository()

    user = asyncio.run(
        user_repo.create(
            name="Integration User",
            password="pass",
            email="integration@example.com",
            is_verified_seller=False,
        )
    )
    add = asyncio.run(
        add_repo.create(
            seller_id=user.id,
            name="Integration Add",
            description="Integration description",
            category=11,
            images_qty=2,
        )
    )
    task = asyncio.run(moderation_repo.create_pending(add.id))

    stored_add = asyncio.run(add_repo.get(add.id))
    stored_task = asyncio.run(moderation_repo.get(task.id))

    assert stored_add.id == add.id
    assert stored_add.seller_id == user.id
    assert stored_task.id == task.id
    assert stored_task.item_id == add.id
    assert stored_task.status == "pending"


def test_add_delete_integration(clean_db: None) -> None:
    user_repo = UserRepository()
    add_repo = AddRepository()

    user = asyncio.run(
        user_repo.create(
            name="Delete User",
            password="pass",
            email="delete@example.com",
            is_verified_seller=False,
        )
    )
    add = asyncio.run(
        add_repo.create(
            seller_id=user.id,
            name="Delete Add",
            description="Delete me",
            category=1,
            images_qty=0,
        )
    )

    deleted = asyncio.run(add_repo.delete(add.id))

    assert deleted.id == add.id
    with pytest.raises(AddNotFoundError):
        asyncio.run(add_repo.get(add.id))
