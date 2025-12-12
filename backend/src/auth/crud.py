"""CRUD operations for users."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import UserCreate, UserUpdate
from src.auth.security import get_password_hash, verify_password
from src.database.models import User


async def create_user(session: AsyncSession, user_create: UserCreate) -> User:
    """Create a new user."""
    db_user = User(
        email=user_create.email,
        hashed_password=get_password_hash(user_create.password),
        full_name=user_create.full_name,
        is_active=user_create.is_active,
        is_superuser=user_create.is_superuser,
    )
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Get a user by email."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    """Authenticate a user by email and password."""
    user = await get_user_by_email(session, email)
    if not user:
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
