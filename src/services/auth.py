from datetime import datetime, timedelta, UTC
from typing import Optional

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from src.database.db import get_db
from src.conf.config import settings
from src.services.users import UserService
from src.services.cache import get_cached, set_cached


class Hash:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        """Return whether a plaintext password matches its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        """Return a bcrypt hash for a plaintext password."""
        return self.pwd_context.hash(password)


oauth2_scheme = HTTPBearer()


# define a function to generate a new access token
async def create_access_token(data: dict, expires_delta: Optional[int] = None):
    """Create a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + timedelta(seconds=expires_delta)
    else:
        expire = datetime.now(UTC) + timedelta(seconds=settings.JWT_EXPIRATION_SECONDS)
    to_encode.update({"exp": expire})
    # print(to_encode)
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Decode a bearer token and load the identity from Redis or the database."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT
        payload = jwt.decode(
            token.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        # print(payload)
        username = payload["sub"]
        if username is None:
            raise credentials_exception
    except (JWTError, KeyError):
        raise credentials_exception

    cached_user = await get_cached(f"auth:user:{username}")
    if cached_user:
        from src.database.models import User

        return User(**cached_user)

    user_service = UserService(db)
    user = await user_service.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    await set_cached(
        f"auth:user:{username}",
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "role": user.role,
        },
        settings.JWT_EXPIRATION_SECONDS,
    )
    return user


async def get_current_admin(user=Depends(get_current_user)):
    """Require the authenticated user to have the administrator role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Тільки адміністратори мають доступ до цієї операції",
        )
    return user


def create_email_token(data: dict):
    """Create a seven-day token used for email verification."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=7)
    to_encode.update({"iat": datetime.now(UTC), "exp": expire})
    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token


async def get_email_from_token(token: str):
    """Validate an email verification token and return its subject."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        email = payload["sub"]
        return email
    except (JWTError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Невірний токен для перевірки електронної пошти",
        )


def create_password_reset_token(email: str) -> str:
    """Create a short-lived token scoped to password reset requests."""
    expire = datetime.now(UTC) + timedelta(
        seconds=settings.PASSWORD_RESET_EXPIRATION_SECONDS
    )
    return jwt.encode(
        {"sub": email, "purpose": "password_reset", "exp": expire},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


async def get_email_from_reset_token(token: str) -> str:
    """Validate a reset token and return its email subject."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("purpose") != "password_reset" or not payload.get("sub"):
            raise JWTError
        return payload["sub"]
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Невірний або прострочений токен скидання пароля",
        )
