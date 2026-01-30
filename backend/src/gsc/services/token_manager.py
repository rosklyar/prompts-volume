"""Token encryption/decryption for secure storage."""

from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken

from src.gsc.exceptions import GSCConfigurationError


class TokenManager:
    """Manages encryption/decryption of OAuth tokens.

    Uses Fernet symmetric encryption for tokens at rest.
    """

    # Refresh tokens 5 minutes before actual expiry
    EXPIRY_BUFFER_MINUTES = 5

    def __init__(self, *, encryption_key: str):
        if not encryption_key:
            raise GSCConfigurationError("GSC token encryption key not configured")
        try:
            self._fernet = Fernet(encryption_key.encode())
        except (ValueError, TypeError) as e:
            raise GSCConfigurationError(f"Invalid encryption key format: {e}")

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a token for storage."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a stored token."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as e:
            raise GSCConfigurationError(f"Failed to decrypt token: {e}")

    def is_token_expired(self, expires_at: datetime) -> bool:
        """Check if token is expired or will expire soon.

        Returns True if token expires within EXPIRY_BUFFER_MINUTES.
        """
        buffer = timedelta(minutes=self.EXPIRY_BUFFER_MINUTES)
        return datetime.now(timezone.utc) >= (expires_at - buffer)

    def calculate_expiry(self, expires_in_seconds: int) -> datetime:
        """Calculate token expiry datetime from expires_in value."""
        return datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
