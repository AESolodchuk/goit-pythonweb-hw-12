from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.services.auth import (
    Hash,
    create_access_token,
    create_email_token,
    create_password_reset_token,
    get_current_admin,
    get_current_user,
    get_email_from_token,
    get_email_from_reset_token,
)
from src.services import cache


@pytest.mark.asyncio
async def test_reset_token_round_trip():
    token = create_password_reset_token("alice@example.com")
    assert await get_email_from_reset_token(token) == "alice@example.com"


@pytest.mark.asyncio
async def test_admin_dependency_rejects_regular_user():
    with pytest.raises(HTTPException) as error:
        await get_current_admin(type("User", (), {"role": "user"})())
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_current_user_uses_cache():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    cached = {"id": 1, "username": "alice", "email": "alice@example.com", "avatar": None, "role": "user"}
    with patch("src.services.auth.jwt.decode", return_value={"sub": "alice"}), patch(
        "src.services.auth.get_cached", new=AsyncMock(return_value=cached)
    ), patch("src.services.auth.UserService.get_user_by_username", new=AsyncMock()) as query:
        user = await get_current_user(credentials, AsyncMock())

    assert user.username == "alice"
    query.assert_not_awaited()


@pytest.mark.asyncio
async def test_current_user_loads_and_caches_database_user():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    user = MagicMock(id=1, username="alice", email="alice@example.com", avatar=None, role="user")
    with patch("src.services.auth.jwt.decode", return_value={"sub": "alice"}), patch(
        "src.services.auth.get_cached", new=AsyncMock(return_value=None)
    ), patch("src.services.auth.UserService.get_user_by_username", new=AsyncMock(return_value=user)), patch(
        "src.services.auth.set_cached", new=AsyncMock()
    ) as set_cache:
        assert await get_current_user(credentials, AsyncMock()) is user
    set_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_current_user_rejects_missing_database_user():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with patch("src.services.auth.jwt.decode", return_value={"sub": "missing"}), patch(
        "src.services.auth.get_cached", new=AsyncMock(return_value=None)
    ), patch("src.services.auth.UserService.get_user_by_username", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as error:
            await get_current_user(credentials, AsyncMock())
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_current_user_rejects_invalid_token():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with patch("src.services.auth.jwt.decode", side_effect=KeyError):
        with pytest.raises(HTTPException) as error:
            await get_current_user(credentials, AsyncMock())
    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_admin_dependency_accepts_admin():
    user = type("User", (), {"role": "admin"})()
    assert await get_current_admin(user) is user


@pytest.mark.asyncio
async def test_reset_token_rejects_wrong_purpose():
    token = await create_access_token({"sub": "alice@example.com"})
    with pytest.raises(HTTPException) as error:
        await get_email_from_reset_token(token)
    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_email_token_round_trip():
    token = create_email_token({"sub": "alice@example.com"})
    assert await get_email_from_token(token) == "alice@example.com"


def test_hash_round_trip():
    hashed = Hash().get_password_hash("password123")
    assert Hash().verify_password("password123", hashed)
    assert not Hash().verify_password("wrong", hashed)


@pytest.mark.asyncio
async def test_cache_helpers_handle_redis_operations():
    client = AsyncMock()
    client.get.return_value = '{"id": 1}'
    with patch("src.services.cache.get_redis", return_value=client):
        assert await cache.get_cached("key") == {"id": 1}
        await cache.set_cached("key", {"id": 1}, 60)
        await cache.delete_cached("key")
    client.get.assert_awaited_once_with("key")
    client.set.assert_awaited_once()
    client.delete.assert_awaited_once_with("key")
    assert client.aclose.await_count == 3


@pytest.mark.asyncio
async def test_cache_helpers_fall_back_when_redis_fails():
    client = AsyncMock()
    client.get.side_effect = RuntimeError("redis unavailable")
    client.set.side_effect = RuntimeError("redis unavailable")
    client.delete.side_effect = RuntimeError("redis unavailable")
    with patch("src.services.cache.get_redis", return_value=client):
        assert await cache.get_cached("key") is None
        await cache.set_cached("key", {"id": 1}, 60)
        await cache.delete_cached("key")
    assert client.aclose.await_count == 3
