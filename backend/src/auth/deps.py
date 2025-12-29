"""Authentication dependencies for FastAPI."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import security
from src.auth.models import TokenPayload
from src.config.settings import settings
from src.database.users_models import User
from src.database.users_session import get_users_session
from src.database.session import get_async_session

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/login/access-token")

# Session dependencies
SessionDep = Annotated[AsyncSession, Depends(get_async_session)]  # prompts_db
UsersSessionDep = Annotated[AsyncSession, Depends(get_users_session)]  # users_db
TokenDep = Annotated[str, Depends(reusable_oauth2)]


async def get_current_user(session: UsersSessionDep, token: TokenDep) -> User:
    """Get the current authenticated user from JWT token."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    if token_data.sub is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = await session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    if user.is_deleted:
        raise HTTPException(status_code=400, detail="User account deleted")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    """Check if the current user is a superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user
