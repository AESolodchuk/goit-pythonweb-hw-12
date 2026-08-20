from pathlib import Path

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr

from src.services.auth import create_email_token
from src.conf.config import settings

def get_mail_config() -> ConnectionConfig:
    """Build the mail configuration when an email is about to be sent."""
    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=settings.USE_CREDENTIALS,
        VALIDATE_CERTS=settings.VALIDATE_CERTS,
        TEMPLATE_FOLDER=Path(__file__).parent / "templates",
    )


async def send_email(email: EmailStr, username: str, host: str):
    try:
        token_verification = create_email_token({"sub": email})
        message = MessageSchema(
            subject="Confirm your email",
            recipients=[email],
            template_body={
                "host": host,
                "username": username,
                "token": token_verification,
            },
            subtype=MessageType.html,
        )

        fm = FastMail(get_mail_config())
        await fm.send_message(message, template_name="verify_email.html")
    except ConnectionErrors as err:
        print(err)


async def send_password_reset_email(
    email: EmailStr, username: str, host: str, token: str
):
    """Send a short-lived password reset link to the account email."""
    try:
        message = MessageSchema(
            subject="Password reset",
            recipients=[email],
            template_body={"host": host, "username": username, "token": token},
            subtype=MessageType.html,
        )
        await FastMail(get_mail_config()).send_message(
            message, template_name="reset_password.html"
        )
    except ConnectionErrors as err:
        print(err)
