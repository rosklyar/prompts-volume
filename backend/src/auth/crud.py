"""CRUD operations for users."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import UserCreate, UserUpdate
from src.auth.security import get_password_hash, verify_password
from src.auth.verification import (
    generate_token_expiry,
    generate_verification_token,
    hash_token,
)
from src.config.settings import settings
from src.database.users_models import CreditGrant, CreditSource, User


async def count_signup_bonuses(session: AsyncSession) -> int:
    """Count how many signup bonuses have been granted."""
    result = await session.scalar(
        select(func.count()).select_from(CreditGrant).where(
            CreditGrant.source == CreditSource.SIGNUP_BONUS
        )
    )
    return result or 0


async def create_user(session: AsyncSession, user_create: UserCreate) -> User:
    """Create a new user with initial signup credits (admin-created, already verified)."""
    db_user = User(
        email=user_create.email,
        hashed_password=get_password_hash(user_create.password),
        full_name=user_create.full_name,
        is_active=user_create.is_active,
        is_superuser=user_create.is_superuser,
        email_verified=True,  # Admin-created users are pre-verified
    )
    session.add(db_user)
    await session.flush()  # Get the user ID

    # Grant initial signup credits if limit not reached
    if (
        settings.billing_max_signup_bonuses is None
        or await count_signup_bonuses(session) < settings.billing_max_signup_bonuses
    ):
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.billing_signup_credits_expiry_days
        )
        credit_grant = CreditGrant(
            user_id=db_user.id,
            source=CreditSource.SIGNUP_BONUS,
            original_amount=Decimal(str(settings.billing_signup_credits)),
            remaining_amount=Decimal(str(settings.billing_signup_credits)),
            expires_at=expires_at,
        )
        session.add(credit_grant)

    await session.commit()
    await session.refresh(db_user)
    return db_user


async def create_user_with_verification(
    session: AsyncSession,
    user_create: UserCreate,
    token_expire_hours: int,
) -> tuple[User, str]:
    """Create a new user requiring email verification.

    Returns:
        Tuple of (user, raw_verification_token)
        - User is created with is_active=False, email_verified=False
        - raw_verification_token should be sent in the verification email
    """
    raw_token, hashed_token = generate_verification_token()
    token_expiry = generate_token_expiry(token_expire_hours)

    db_user = User(
        email=user_create.email,
        hashed_password=get_password_hash(user_create.password),
        full_name=user_create.full_name,
        is_active=False,  # Inactive until email verified
        is_superuser=False,  # Public signup cannot create superusers
        email_verified=False,
        email_verification_token=hashed_token,
        email_verification_token_expires_at=token_expiry,
    )
    session.add(db_user)
    # No credit grant until email is verified

    await session.commit()
    await session.refresh(db_user)
    return db_user, raw_token


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Get a user by email."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    """Authenticate a user by email and password."""
    user = await get_user_by_email(session, email)
    if not user:
        return None
    if user.is_deleted:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def update_user(session: AsyncSession, db_user: User, user_in: UserUpdate) -> User:
    """Update a user."""
    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    for field, value in update_data.items():
        setattr(db_user, field, value)
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user


async def get_user_by_verification_token(
    session: AsyncSession, raw_token: str
) -> User | None:
    """Get user by verification token."""
    hashed_token = hash_token(raw_token)
    result = await session.execute(
        select(User).where(User.email_verification_token == hashed_token)
    )
    return result.scalar_one_or_none()


async def verify_user_email(session: AsyncSession, user: User) -> User:
    """Mark user email as verified, activate account, and grant signup credits if limit not reached."""
    user.email_verified = True
    user.is_active = True
    user.email_verification_token = None
    user.email_verification_token_expires_at = None
    session.add(user)

    # Grant signup credits if limit not reached
    if (
        settings.billing_max_signup_bonuses is None
        or await count_signup_bonuses(session) < settings.billing_max_signup_bonuses
    ):
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.billing_signup_credits_expiry_days
        )
        credit_grant = CreditGrant(
            user_id=user.id,
            source=CreditSource.SIGNUP_BONUS,
            original_amount=Decimal(str(settings.billing_signup_credits)),
            remaining_amount=Decimal(str(settings.billing_signup_credits)),
            expires_at=expires_at,
        )
        session.add(credit_grant)

    await session.commit()
    await session.refresh(user)
    return user


async def regenerate_verification_token(
    session: AsyncSession, user: User, expire_hours: int
) -> str:
    """Generate a new verification token for a user.

    Returns:
        Raw token to send in email
    """
    raw_token, hashed_token = generate_verification_token()
    user.email_verification_token = hashed_token
    user.email_verification_token_expires_at = generate_token_expiry(expire_hours)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return raw_token
