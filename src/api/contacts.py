from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.conf import messages
from src.database.db import get_db
from src.database.models import User
from src.schemas.contacts import ContactBase, ContactBirthdayRequest, ContactResponse
from src.services.auth import get_current_user
from src.services.contacts import ContactService

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("/", response_model=List[ContactResponse], status_code=status.HTTP_200_OK)
async def read_contacts(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return a paginated list of contacts for the current user."""

    contact_service = ContactService(db)
    contacts = await contact_service.get_contacts(skip, limit, user)
    return contacts


@router.get("/{contact_id}", response_model=ContactResponse)
async def read_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Retrieve a contact by its ID.

    Args:
        contact_id (int): The ID of the contact to retrieve.
        db (AsyncSession, optional): The database session dependency.

    Returns:
        Contact: The contact object if found.

    Raises:
        HTTPException: If the contact is not found, raises a 404 HTTP exception.
    """
    contact_service = ContactService(db)
    contact = await contact_service.get_contact(contact_id, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=messages.CONTACT_NOT_FOUND
        )
    return contact


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactBase,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new contact.

    Args:
        body (ContactBase): The contact data to be created.
        db (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        dict: The created contact data.
    """
    contact_service = ContactService(db)
    return await contact_service.create_contact(body, user)


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    body: ContactBase,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update an existing contact.

    Args:
        body (ContactBase): The updated contact information.
        contact_id (int): The ID of the contact to update.
        db (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        Contact: The updated contact information.

    Raises:
        HTTPException: If the contact with the given ID is not found.
    """
    contact_service = ContactService(db)
    contact = await contact_service.update_contact(contact_id, body, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=messages.CONTACT_NOT_FOUND
        )
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Removes a contact by its ID.

    Args:
        contact_id (int): The ID of the contact to be removed.
        db (AsyncSession, optional): The database session dependency. Defaults to Depends(get_db).

    Raises:
        HTTPException: If the contact is not found, raises a 404 HTTP exception with a relevant message.

    Returns:
        None
    """
    contact_service = ContactService(db)
    contact = await contact_service.remove_contact(contact_id, user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=messages.CONTACT_NOT_FOUND
        )
    return


@router.get("/search/", response_model=List[ContactResponse])
async def search_contacts(
    text: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Search for contacts based on a text query.

    Args:
        text (str): The text to search for in contacts.
        skip (int, optional): The number of records to skip for pagination. Defaults to 0.
        limit (int, optional): The maximum number of records to return. Defaults to 100.
        db (AsyncSession, optional): The database session dependency.

    Returns:
        List[Contact]: A list of contacts that match the search criteria.
    """
    contact_service = ContactService(db)
    contacts = await contact_service.search_contacts(text, skip, limit, user)
    return contacts


@router.post("/upcoming-birthdays", response_model=List[ContactResponse])
async def upcoming_birthdays(
    body: ContactBirthdayRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Fetch contacts with upcoming birthdays within a specified number of days.

    Args:
        body (ContactBirthdayRequest): The request body containing the number of days to look ahead for upcoming birthdays.
        db (AsyncSession, optional): The database session dependency. Defaults to Depends(get_db).

    Returns:
        List[Contact]: A list of contacts with birthdays within the specified number of days.
    """
    contact_service = ContactService(db)
    contacts = await contact_service.upcoming_birthdays(body.days, user)
    return contacts
