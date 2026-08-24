from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from src.database.db import get_db
from src.services.auth import get_current_admin, get_current_user


def _user(username="alice", email="alice@example.com", role="user"):
    return MagicMock(id=1, username=username, email=email, role=role, avatar=None)


def _contact(contact_id=1):
    return MagicMock(
        id=contact_id,
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
        phone_number="+380501234567",
        birthday=date(1990, 1, 1),
        additional_data=None,
        created_at=datetime(2026, 1, 1),
        updated_at=None,
    )


def _override_user(user=None):
    app.dependency_overrides[get_current_user] = lambda: user or _user()
    app.dependency_overrides[get_db] = lambda: AsyncMock()


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


def test_register_route_creates_user_and_schedules_email():
    created_user = _user()
    _override_user()
    try:
        with patch(
            "src.api.auth.UserService.get_user_by_email", new=AsyncMock(return_value=None)
        ), patch(
            "src.api.auth.UserService.get_user_by_username", new=AsyncMock(return_value=None)
        ), patch(
            "src.api.auth.UserService.create_user", new=AsyncMock(return_value=created_user)
        ), patch("src.api.auth.send_email"):
            with TestClient(app) as client:
                response = client.post(
                    "/api/auth/register",
                    json={
                        "username": "alice",
                        "email": "alice@example.com",
                        "password": "secret123",
                    },
                )
        assert response.status_code == 201
        assert response.json()["email"] == "alice@example.com"
    finally:
        app.dependency_overrides.clear()


def test_login_route_returns_access_token():
    user = MagicMock(hashed_password="hashed", username="alice", email="alice@example.com")
    _override_user()
    try:
        with patch(
            "src.api.auth.UserService.get_user_by_email", new=AsyncMock(return_value=user)
        ), patch("src.api.auth.Hash.verify_password", return_value=True), patch(
            "src.api.auth.create_access_token", new=AsyncMock(return_value="access-token")
        ):
            with TestClient(app) as client:
                response = client.post(
                    "/api/auth/login",
                    json={"email": "alice@example.com", "password": "secret123"},
                )
        assert response.status_code == 200
        assert response.json() == {"access_token": "access-token", "token_type": "bearer"}
    finally:
        app.dependency_overrides.clear()


def test_contacts_routes_support_list_create_update_delete_and_search():
    contact = _contact()
    _override_user()
    try:
        with patch("src.api.contacts.ContactService.get_contacts", new=AsyncMock(return_value=[contact])), patch(
            "src.api.contacts.ContactService.create_contact", new=AsyncMock(return_value=contact)
        ), patch("src.api.contacts.ContactService.update_contact", new=AsyncMock(return_value=contact)), patch(
            "src.api.contacts.ContactService.remove_contact", new=AsyncMock(return_value=contact)
        ), patch("src.api.contacts.ContactService.search_contacts", new=AsyncMock(return_value=[contact])):
            with TestClient(app) as client:
                payload = {
                    "first_name": "Alice",
                    "last_name": "Smith",
                    "email": "alice@example.com",
                    "phone_number": "+380501234567",
                    "birthday": "1990-01-01",
                    "additional_data": None,
                }
                assert client.get("/api/contacts/").status_code == 200
                assert client.post("/api/contacts/", json=payload).status_code == 201
                assert client.put("/api/contacts/1", json=payload).status_code == 200
                assert client.delete("/api/contacts/1").status_code == 204
                assert client.get("/api/contacts/search/?text=Alice").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_current_user_route_returns_profile():
    _override_user(_user(username="current", email="current@example.com"))
    try:
        with TestClient(app) as client:
            response = client.get("/api/users/me")
        assert response.status_code == 200
        assert response.json()["username"] == "current"
    finally:
        app.dependency_overrides.clear()


def test_confirmed_email_route_confirms_existing_user():
    user = _user(email="alice@example.com")
    user.confirmed = False
    _override_user()
    try:
        with patch(
            "src.api.auth.get_email_from_token", new=AsyncMock(return_value="alice@example.com")
        ), patch(
            "src.api.auth.UserService.get_user_by_email", new=AsyncMock(return_value=user)
        ), patch("src.api.auth.UserService.confirmed_email", new=AsyncMock()) as confirm:
            with TestClient(app) as client:
                response = client.get("/api/auth/confirmed_email/verification-token")
        assert response.status_code == 200
        confirm.assert_awaited_once_with("alice@example.com")
    finally:
        app.dependency_overrides.clear()
