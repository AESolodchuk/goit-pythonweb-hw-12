from unittest.mock import AsyncMock, MagicMock

import pytest

from src.repository.contacts import ContactRepository
from src.repository.users import UserRepository
from src.schemas.contacts import ContactBase
from src.schemas.users import UserCreate


@pytest.mark.asyncio
async def test_user_repository_get_by_username():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = "user"
    session.execute.return_value = result

    found = await UserRepository(session).get_user_by_username("alice")

    assert found == "user"
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_repository_update_password_missing_user():
    repository = UserRepository(AsyncMock())
    repository.get_user_by_email = AsyncMock(return_value=None)

    assert await repository.update_password("missing@example.com", "hash") is None


@pytest.mark.asyncio
async def test_user_repository_reads_and_writes_users():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = "user"
    session.execute.return_value = result
    repository = UserRepository(session)

    assert await repository.get_user_by_id(1) == "user"
    assert await repository.get_user_by_email("a@example.com") == "user"
    body = UserCreate(username="alice", email="a@example.com", password="hash")
    created = await repository.create_user(body)
    assert created is session.add.call_args.args[0]
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_user_repository_updates_existing_user_and_confirms_email():
    session = AsyncMock()
    user = MagicMock(username="alice")
    repository = UserRepository(session)
    repository.get_user_by_email = AsyncMock(return_value=user)

    await repository.confirmed_email("a@example.com")
    updated = await repository.update_password("a@example.com", "new-hash")

    assert user.confirmed is True
    assert user.hashed_password == "new-hash"
    assert updated is user
    assert session.commit.await_count == 2


@pytest.mark.asyncio
async def test_user_repository_updates_avatar():
    session = AsyncMock()
    user = MagicMock(username="alice")
    repository = UserRepository(session)
    repository.get_user_by_email = AsyncMock(return_value=user)

    assert await repository.update_avatar_url("a@example.com", "avatar") is user
    assert user.avatar == "avatar"


@pytest.mark.asyncio
async def test_contact_repository_get_contacts_scopes_by_user_id():
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["contact"]
    session.execute.return_value = result
    user = MagicMock(id=7)

    found = await ContactRepository(session).get_contacts(0, 10, user)

    assert found == ["contact"]
    statement = session.execute.await_args.args[0]
    assert statement.compile().params["user_id_1"] == 7


@pytest.mark.asyncio
async def test_contact_repository_crud_and_search_methods():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    repository = ContactRepository(session)
    user = MagicMock(id=7)
    body = ContactBase(
        first_name="Alice", last_name="Brown", email="a@example.com", phone_number="123456", birthday="2000-01-01", additional_data=None
    )

    assert await repository.get_contact_by_id(1, user) is None
    assert await repository.remove_contact(1, user) is None
    assert await repository.update_contact(1, body, user) is None
    assert await repository.search_contacts("A", 0, 10, user) == []
    assert await repository.upcoming_birthdays(7, user) == []
