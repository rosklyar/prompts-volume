"""Security utilities for authentication."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from src.config.settings import settings

ALGORITHM = "HS256"


def create_access_token(subject: str, expires_delta: timedelta) -> str:
    """Create a JWT access token."""
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
