from sqlalchemy.ext.asyncio import AsyncSession
from libgravatar import Gravatar

from src.repository.users import UserRepository
from src.schemas.users import UserCreate
from src.services.cache import delete_cached


class UserService:
    """Coordinate user account operations and cache invalidation."""

    def __init__(self, db: AsyncSession):
        """Create a service backed by an async database session."""
        self.repository = UserRepository(db)

    async def create_user(self, body: UserCreate):
        """Create a user and derive a default Gravatar avatar when possible."""
        avatar = None
        try:
            g = Gravatar(body.email)
            avatar = g.get_image()
        except Exception as e:
            print(e)

        return await self.repository.create_user(body, avatar)

    async def get_user_by_id(self, user_id: int):
        """Return a user by database identifier."""
        return await self.repository.get_user_by_id(user_id)

    async def get_user_by_username(self, username: str):
        """Return a user by username."""
        return await self.repository.get_user_by_username(username)

    async def get_user_by_email(self, email: str):
        """Return a user by email address."""
        return await self.repository.get_user_by_email(email)

    async def confirmed_email(self, email: str) -> None:
        """Mark a user's email address as confirmed."""
        return await self.repository.confirmed_email(email)

    async def update_avatar_url(self, email: str, url: str):
        """Update an avatar URL and invalidate the cached identity."""
        user = await self.repository.update_avatar_url(email, url)
        if user:
            await delete_cached(f"auth:user:{user.username}")
        return user

    async def update_password(self, email: str, hashed_password: str):
        """Update a password and invalidate the user's cached identity."""
        user = await self.repository.update_password(email, hashed_password)
        if user:
            await delete_cached(f"auth:user:{user.username}")
        return user
