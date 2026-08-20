from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.contacts import ContactBase
from src.schemas.users import UserCreate
from src.services.contacts import ContactService
from src.services.users import UserService


@pytest.mark.asyncio
async def test_contact_service_delegates_operations():
    repository = AsyncMock()
    service = ContactService(AsyncMock())
    service.contact_repository = repository
    user = MagicMock()
    body = MagicMock(spec=ContactBase)

    await service.create_contact(body, user)
    await service.get_contacts(0, 10, user)
    await service.get_contact(1, user)
    await service.update_contact(1, body, user)
    await service.remove_contact(1, user)
    await service.search_contacts("alice", 0, 10, user)
    await service.upcoming_birthdays(7, user)

    assert repository.create_contact.await_count == 1
    assert repository.get_contacts.await_count == 1
    assert repository.get_contact_by_id.await_count == 1
    assert repository.update_contact.await_count == 1
    assert repository.remove_contact.await_count == 1
    assert repository.search_contacts.await_count == 1
    assert repository.upcoming_birthdays.await_count == 1


@pytest.mark.asyncio
async def test_user_service_delegates_account_operations():
    repository = AsyncMock()
    service = UserService(AsyncMock())
    service.repository = repository
    body = UserCreate(username="alice", email="alice@example.com", password="hash")
    user = MagicMock(username="alice", email="alice@example.com")
    repository.create_user.return_value = user
    repository.get_user_by_id.return_value = user
    repository.get_user_by_username.return_value = user
    repository.get_user_by_email.return_value = user
    repository.update_avatar_url.return_value = user
    repository.update_password.return_value = user

    with patch("src.services.users.Gravatar") as gravatar:
        gravatar.return_value.get_image.return_value = "avatar"
        assert await service.create_user(body) is user
    assert await service.get_user_by_id(1) is user
    assert await service.get_user_by_username("alice") is user
    assert await service.get_user_by_email("alice@example.com") is user
    await service.confirmed_email("alice@example.com")
    assert await service.update_avatar_url("alice@example.com", "new-avatar") is user
    assert await service.update_password("alice@example.com", "new-hash") is user


@pytest.mark.asyncio
async def test_user_service_skips_cache_invalidation_when_update_missing():
    service = UserService(AsyncMock())
    service.repository.update_avatar_url = AsyncMock(return_value=None)
    service.repository.update_password = AsyncMock(return_value=None)

    with patch("src.services.users.delete_cached", new=AsyncMock()) as delete_cached:
        assert await service.update_avatar_url("missing@example.com", "avatar") is None
        assert await service.update_password("missing@example.com", "hash") is None
    delete_cached.assert_not_awaited()
