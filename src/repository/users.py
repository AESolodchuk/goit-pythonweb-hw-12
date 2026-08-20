from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.schemas.users import UserCreate


class UserRepository:
    """Persist and retrieve user accounts using an async SQLAlchemy session."""

    def __init__(self, session: AsyncSession):
        """Initialize the repository with an async database session."""
        self.db = session

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Return a user by primary key."""
        stmt = select(User).filter_by(id=user_id)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        """Return a user by username."""
        stmt = select(User).filter_by(username=username)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Return a user by email address."""
        stmt = select(User).filter_by(email=email)
        user = await self.db.execute(stmt)
        return user.scalar_one_or_none()

    async def create_user(self, body: UserCreate, avatar: str = None) -> User:
        """Create and persist a new user account."""
        user = User(
            **body.model_dump(exclude_unset=True, exclude={"password"}),
            hashed_password=body.password,
            avatar=avatar
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def confirmed_email(self, email: str) -> None:
        """Mark the user's email address as confirmed."""
        user = await self.get_user_by_email(email)
        user.confirmed = True
        await self.db.commit()

    async def update_avatar_url(self, email: str, url: str) -> User:
        """Replace a user's avatar URL."""
        user = await self.get_user_by_email(email)
        user.avatar = url
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_password(self, email: str, hashed_password: str) -> User | None:
        """Replace the stored password hash for a user."""
        user = await self.get_user_by_email(email)
        if user is None:
            return None
        user.hashed_password = hashed_password
        await self.db.commit()
        await self.db.refresh(user)
        return user
