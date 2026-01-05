"""Email verification token generation and validation."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone


def generate_verification_token() -> tuple[str, str]:
    """Generate a verification token.

    Returns:
        Tuple of (raw_token, hashed_token)
        - raw_token: Send to user in email (URL-safe)
        - hashed_token: Store in database
    """
    raw_token = secrets.token_urlsafe(32)  # 256 bits of entropy
    hashed_token = hash_token(raw_token)
    return raw_token, hashed_token


def hash_token(raw_token: str) -> str:
    """Hash a raw token for database storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def generate_token_expiry(hours: int) -> datetime:
    """Generate token expiry datetime."""
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def is_token_expired(expires_at: datetime | None) -> bool:
    """Check if a token has expired."""
    if expires_at is None:
        return True
    return datetime.now(timezone.utc) > expires_at
