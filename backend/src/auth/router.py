"""Authentication API routes."""

import logging
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select

from src.auth import crud, security
from src.auth.deps import CurrentUser, UsersSessionDep, get_current_active_superuser
from src.auth.models import (
    Message,
    ResendVerificationRequest,
    SignupResponse,
    Token,
    UpdatePassword,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
    VerifyEmailResponse,
)
from src.auth.verification import is_token_expired
from src.config.settings import settings
from src.database.users_models import User
from src.email.services.email_service import EmailService
from src.email.services.verification_email_service import VerificationEmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["auth"])


def get_email_service() -> EmailService:
    """Get email service instance."""
    return EmailService(
        api_key=settings.brevo_api_key,
        sender_email=settings.brevo_sender_email,
        sender_name=settings.brevo_sender_name,
    )


def get_verification_email_service() -> VerificationEmailService:
    """Get verification email service instance."""
    return VerificationEmailService(
        email_service=get_email_service(),
        frontend_url=settings.frontend_url,
        expires_in_hours=settings.email_verification_token_expire_hours,
    )


# Login endpoints
@router.post("/login/access-token")
async def login_access_token(
    session: UsersSessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """OAuth2 compatible token login, get an access token for future requests."""
    user = await crud.authenticate(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.email_verified:
        raise HTTPException(
            status_code=400,
            detail="Please verify your email before logging in. Check your inbox for the verification link.",
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


@router.post("/login/test-token", response_model=UserPublic)
async def test_token(current_user: CurrentUser) -> Any:
    """Test access token validity."""
    return current_user


# User endpoints
@router.get(
    "/users/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
async def read_users(session: UsersSessionDep, skip: int = 0, limit: int = 100) -> Any:
    """Retrieve users (superuser only)."""
    count = await session.scalar(select(func.count()).select_from(User))
    result = await session.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return UsersPublic(data=users, count=count or 0)


@router.post(
    "/users/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
async def create_user(session: UsersSessionDep, user_in: UserCreate) -> Any:
    """Create new user (superuser only)."""
    user = await crud.get_user_by_email(session, user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    return await crud.create_user(session, user_in)


@router.post("/users/signup", response_model=SignupResponse)
async def register_user(session: UsersSessionDep, user_in: UserRegister) -> Any:
    """Create new user and send verification email."""
    user = await crud.get_user_by_email(session, user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate(
        email=user_in.email,
        password=user_in.password,
        full_name=user_in.full_name,
    )
    db_user, raw_token = await crud.create_user_with_verification(
        session, user_create, settings.email_verification_token_expire_hours
    )

    # Send verification email (fire and forget - don't fail signup if email fails)
    verification_service = get_verification_email_service()
    email_sent = verification_service.send_verification_email(
        to_email=db_user.email,
        user_name=db_user.full_name,
        verification_token=raw_token,
    )
    if not email_sent:
        logger.warning(f"Failed to send verification email to {db_user.email}")

    return SignupResponse(
        message="Registration successful. Please check your email to verify your account.",
        email=db_user.email,
    )


@router.get("/users/me", response_model=UserPublic)
async def read_user_me(current_user: CurrentUser) -> Any:
    """Get current user."""
    return current_user


@router.patch("/users/me", response_model=UserPublic)
async def update_user_me(
    session: UsersSessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """Update own user."""
    if user_in.email:
        existing_user = await crud.get_user_by_email(session, user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=409, detail="User with this email already exists")
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return current_user


@router.patch("/users/me/password", response_model=Message)
async def update_password_me(
    session: UsersSessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """Update own password."""
    if not security.verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    current_user.hashed_password = security.get_password_hash(body.new_password)
    session.add(current_user)
    await session.commit()
    return Message(message="Password updated successfully")


@router.delete("/users/me", response_model=Message)
async def delete_user_me(session: UsersSessionDep, current_user: CurrentUser) -> Any:
    """Delete own user."""
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    await session.delete(current_user)
    await session.commit()
    return Message(message="User deleted successfully")


@router.get("/users/{user_id}", response_model=UserPublic)
async def read_user_by_id(
    user_id: str, session: UsersSessionDep, current_user: CurrentUser
) -> Any:
    """Get a specific user by id."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    return user


@router.patch(
    "/users/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
async def update_user(
    session: UsersSessionDep,
    user_id: str,
    user_in: UserUpdate,
) -> Any:
    """Update a user (superuser only)."""
    db_user = await session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = await crud.get_user_by_email(session, user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=409, detail="User with this email already exists")
    return await crud.update_user(session, db_user, user_in)


@router.delete(
    "/users/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
async def delete_user(
    session: UsersSessionDep, current_user: CurrentUser, user_id: str
) -> Message:
    """Delete a user (superuser only)."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    await session.delete(user)
    await session.commit()
    return Message(message="User deleted successfully")


# Email verification endpoints
@router.get("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(session: UsersSessionDep, token: str) -> Any:
    """Verify user email address.

    This endpoint is called when user clicks the verification link in their email.
    """
    user = await crud.get_user_by_verification_token(session, token)

    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    if is_token_expired(user.email_verification_token_expires_at):
        raise HTTPException(
            status_code=400,
            detail="Verification token has expired. Please request a new one.",
        )

    if user.email_verified:
        return VerifyEmailResponse(
            message="Email already verified", status="already_verified"
        )

    await crud.verify_user_email(session, user)

    return VerifyEmailResponse(message="Email verified successfully", status="success")


@router.post("/resend-verification", response_model=Message)
async def resend_verification(
    session: UsersSessionDep, request: ResendVerificationRequest
) -> Any:
    """Resend verification email."""
    user = await crud.get_user_by_email(session, request.email)

    # Don't reveal if email exists - return generic response
    if not user:
        return Message(
            message="If an account exists with this email, a verification link will be sent."
        )

    if user.email_verified:
        return Message(message="Email is already verified. You can log in.")

    raw_token = await crud.regenerate_verification_token(
        session, user, settings.email_verification_token_expire_hours
    )

    verification_service = get_verification_email_service()
    email_sent = verification_service.send_verification_email(
        to_email=user.email,
        user_name=user.full_name,
        verification_token=raw_token,
    )
    if not email_sent:
        logger.warning(f"Failed to resend verification email to {user.email}")

    return Message(message="Verification email sent. Please check your inbox.")
