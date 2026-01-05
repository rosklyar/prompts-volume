"""Pydantic models for email data."""

from pydantic import BaseModel, EmailStr


class EmailMessage(BaseModel):
    """Model for email messages."""

    to_email: EmailStr
    to_name: str | None = None
    subject: str
    html_content: str
    text_content: str | None = None


class VerificationEmailData(BaseModel):
    """Data for verification email template."""

    user_name: str
    verification_url: str
    expires_in_hours: int = 24
