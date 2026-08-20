from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from src.database.db import get_db
from src.services.auth import get_current_user
from src.services.auth import get_current_admin


def test_root_route():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_avatar_route_requires_admin():
    app.dependency_overrides[get_current_user] = lambda: type(
        "User", (), {"role": "user"}
    )()
    try:
        with TestClient(app) as client:
            response = client.patch("/api/users/avatar", files={"file": ("a.txt", b"x")})
        assert response.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()


def test_avatar_route_allows_admin_and_updates_profile():
    admin = type("User", (), {"role": "admin", "username": "admin", "email": "a@example.com"})()
    app.dependency_overrides[get_current_admin] = lambda: admin
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    updated = MagicMock(
        id=1, username="admin", email="a@example.com", avatar="https://avatar", role="admin"
    )
    try:
        with patch("src.api.users.UploadFileService.upload_file", return_value="https://avatar"), patch(
            "src.api.users.UserService.update_avatar_url", new=AsyncMock(return_value=updated)
        ):
            with TestClient(app) as client:
                response = client.patch("/api/users/avatar", files={"file": ("a.txt", b"x")})
        assert response.status_code == 200
        assert response.json()["avatar"] == "https://avatar"
    finally:
        app.dependency_overrides.clear()


def test_reset_password_route_changes_password():
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    user = MagicMock(email="alice@example.com")
    try:
        with patch("src.api.auth.get_email_from_reset_token", new=AsyncMock(return_value="alice@example.com")), patch(
            "src.api.auth.UserService.get_user_by_email", new=AsyncMock(return_value=user)
        ), patch("src.api.auth.Hash.get_password_hash", return_value="hashed"), patch(
            "src.api.auth.UserService.update_password", new=AsyncMock(return_value=user)
        ) as update_password:
            with TestClient(app) as client:
                response = client.post(
                    "/api/auth/reset_password",
                    json={"token": "reset-token", "password": "new-password"},
                )
        assert response.status_code == 200
        update_password.assert_awaited_once_with("alice@example.com", "hashed")
    finally:
        app.dependency_overrides.clear()


def test_reset_password_route_rejects_unknown_user():
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    try:
        with patch("src.api.auth.get_email_from_reset_token", new=AsyncMock(return_value="missing@example.com")), patch(
            "src.api.auth.UserService.get_user_by_email", new=AsyncMock(return_value=None)
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/api/auth/reset_password",
                    json={"token": "reset-token", "password": "new-password"},
                )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()
