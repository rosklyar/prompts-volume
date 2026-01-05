"""Pydantic models for authentication."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user model with common fields."""

    email: EmailStr
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    """Model for creating a new user (admin)."""

    password: str = Field(min_length=8, max_length=128)


class UserRegister(BaseModel):
    """Model for public user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class UserPublic(UserBase):
    """Model for public user response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email_verified: bool = False


class UsersPublic(BaseModel):
    """Model for list of users response."""

    data: list[UserPublic]
    count: int


class UserUpdate(BaseModel):
    """Model for updating a user (admin)."""

    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None
    is_superuser: bool | None = None


class UserUpdateMe(BaseModel):
    """Model for user updating their own profile."""

    full_name: str | None = None
    email: EmailStr | None = None


class UpdatePassword(BaseModel):
    """Model for password update."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class Token(BaseModel):
    """JWT token response model."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload model."""

    sub: str | None = None


class Message(BaseModel):
    """Generic message response model."""

    message: str


class SignupResponse(BaseModel):
    """Response after successful public signup."""

    message: str
    email: str


class ResendVerificationRequest(BaseModel):
    """Request to resend verification email."""

    email: EmailStr


class VerifyEmailResponse(BaseModel):
    """Response after email verification attempt."""

    message: str
    status: str  # "success" or "already_verified"
