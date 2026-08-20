""" 
This module defines the `ContactRepository` class, which provides methods for
managing contacts in the database. 
"""

from datetime import timedelta
from typing import List

from sqlalchemy import Integer, and_, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import Contact, User
from src.schemas.contacts import ContactBase, ContactResponse


class ContactRepository:
    """Perform contact persistence scoped to the authenticated user."""

    def __init__(self, session: AsyncSession):
        """Initialize the repository with an async database session."""
        self.db = session

    async def get_contacts(self, skip: int, limit: int, user: User) -> List[Contact]:
        """Return a paginated list of contacts owned by ``user``."""
        stmt = select(Contact).filter_by(user_id=user.id).offset(skip).limit(limit)
        contacts = await self.db.execute(stmt)
        return contacts.scalars().all()

    async def get_contact_by_id(self, contact_id: int, user: User) -> Contact | None:
        """Return one contact by ID when it belongs to ``user``."""
        stmt = select(Contact).filter_by(user_id=user.id, id=contact_id)
        contact = await self.db.execute(stmt)
        return contact.scalar_one_or_none()

    async def create_contact(self, body: ContactBase, user: User) -> Contact:
        """Create and persist a contact for ``user``."""
        contact = Contact(**body.model_dump(exclude_unset=True), user=user)
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def remove_contact(self, contact_id: int, user: User) -> Contact | None:
        """Delete and return a user's contact, or return ``None`` if absent."""
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            await self.db.delete(contact)
            await self.db.commit()
        return contact

    async def update_contact(
        self, contact_id: int, body: ContactBase, user: User
    ) -> Contact | None:
        """Update a user's contact and return it, or return ``None`` if absent."""
        contact = await self.get_contact_by_id(contact_id, user)
        if contact:
            for key, value in body.dict(exclude_unset=True).items():
                setattr(contact, key, value)

            await self.db.commit()
            await self.db.refresh(contact)

        return contact

    async def search_contacts(
        self, search: str, skip: int, limit: int, user: User
    ) -> List[Contact]:
        """Search a user's contacts across their text fields."""
        stmt = (
            select(Contact)
            .filter(
                Contact.user_id == user.id,
                or_(
                    Contact.first_name.ilike(f"%{search}%"),
                    Contact.last_name.ilike(f"%{search}%"),
                    Contact.email.ilike(f"%{search}%"),
                    Contact.additional_data.ilike(f"%{search}%"),
                    Contact.phone_number.ilike(f"%{search}%"),
                ),
            )
            .offset(skip)
            .limit(limit)
        )
        contacts = await self.db.execute(stmt)
        return contacts.scalars().all()

    async def upcoming_birthdays(self, days: int, user: User) -> List[Contact]:
        """Return a user's contacts with birthdays in the next ``days`` days."""
        today = func.current_date()
        future_date = func.current_date() + timedelta(days=days)

        stmt = select(Contact).filter(
            Contact.user_id == user.id,
            or_(
                func.make_date(
                    extract("year", today).cast(Integer),
                    extract("month", Contact.birthday).cast(Integer),
                    extract("day", Contact.birthday).cast(Integer),
                ).between(today, future_date),
                func.make_date(
                    (extract("year", today) + 1).cast(Integer),
                    extract("month", Contact.birthday).cast(Integer),
                    extract("day", Contact.birthday).cast(Integer),
                ).between(today, future_date),
            ),
        )
        # print((stmt))
        contacts = await self.db.execute(stmt)
        return contacts.scalars().all()
