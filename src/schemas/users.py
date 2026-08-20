from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator


# Схема користувача
class User(BaseModel):
    """Public representation of an authenticated user."""

    id: int
    username: str
    email: str
    avatar: str | None
    role: str

    model_config = ConfigDict(from_attributes=True)


# Схема для запиту реєстрації
class UserCreate(BaseModel):
    """Registration payload containing the user's credentials."""

    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    """Login payload used to authenticate a user."""

    email: str
    password: str


# Схема для токену
class Token(BaseModel):
    """Bearer token returned after successful authentication."""

    access_token: str
    token_type: str


class RequestEmail(BaseModel):
    """Payload for requesting email verification."""

    email: EmailStr


class PasswordResetRequest(BaseModel):
    """Payload for requesting a password reset link."""

    email: EmailStr


class PasswordReset(BaseModel):
    """Payload containing a reset token and the replacement password."""

    token: str
    password: str = Field(min_length=8)
