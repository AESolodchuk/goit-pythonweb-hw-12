from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Security,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.schemas.users import (
    PasswordReset,
    PasswordResetRequest,
    RequestEmail,
    Token,
    User,
    UserCreate,
    UserLogin,
)
from src.services.auth import (
    Hash,
    create_access_token,
    create_password_reset_token,
    get_email_from_reset_token,
    get_email_from_token,
)
from src.services.email import send_email, send_password_reset_email
from src.services.users import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


# Реєстрація користувача
@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    """Register a user, hash its password, and send verification email."""
    user_service = UserService(db)

    email_user = await user_service.get_user_by_email(user_data.email)
    if email_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з таким email вже існує",
        )

    username_user = await user_service.get_user_by_username(user_data.username)
    if username_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з таким іменем вже існує",
        )
    user_data.password = Hash().get_password_hash(user_data.password)
    new_user = await user_service.create_user(user_data)
    background_tasks.add_task(
        send_email, new_user.email, new_user.username, request.base_url
    )
    return new_user


# Логін користувача
@router.post("/login", response_model=Token)
async def login_user(body: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a user and return a bearer access token."""
    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)
    if not user or not Hash().verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неправильний логін або пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = await create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/request_email")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    """Send an email-verification message without exposing account existence."""
    user_service = UserService(db)
    user = await user_service.get_user_by_email(body.email)

    if user and user.confirmed:
        return {"message": "Ваша електронна пошта вже підтверджена"}
    if user:
        background_tasks.add_task(
            send_email, user.email, user.username, request.base_url
        )
    return {"message": "Перевірте свою електронну пошту для підтвердження"}


@router.post("/request_password_reset")
async def request_password_reset(
    body: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    """Send a reset link without revealing whether an email is registered."""
    user = await UserService(db).get_user_by_email(body.email)
    if user:
        token = create_password_reset_token(user.email)
        background_tasks.add_task(
            send_password_reset_email, user.email, user.username, request.base_url, token
        )
    return {"message": "Якщо email зареєстровано, посилання для скидання надіслано"}


@router.post("/reset_password")
async def reset_password(body: PasswordReset, db: Session = Depends(get_db)):
    """Set a new password using a valid, short-lived reset token."""
    email = await get_email_from_reset_token(body.token)
    user = await UserService(db).get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Користувача не знайдено")
    await UserService(db).update_password(email, Hash().get_password_hash(body.password))
    return {"message": "Пароль успішно змінено"}


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: Session = Depends(get_db)):
    """Confirm a user's email address using a signed verification token."""
    email = await get_email_from_token(token)
    user_service = UserService(db)
    user = await user_service.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Ваша електронна пошта вже підтверджена"}
    await user_service.confirmed_email(email)
    return {"message": "Електронну пошту підтверджено"}
