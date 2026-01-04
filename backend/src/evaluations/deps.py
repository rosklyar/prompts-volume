"""Dependencies for evaluation endpoints."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from src.config.settings import settings


def get_allowed_tokens() -> set[str]:
    """Parse CSV tokens from settings."""
    if not settings.evaluation_api_tokens:
        return set()
    return {t.strip() for t in settings.evaluation_api_tokens.split(",") if t.strip()}


def verify_bot_secret(
    x_bot_secret: str = Header(..., alias="X-Bot-Secret"),
) -> str:
    """Verify bot secret from X-Bot-Secret header."""
    allowed_tokens = get_allowed_tokens()

    if not allowed_tokens:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No bot secrets configured",
        )

    if x_bot_secret not in allowed_tokens:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bot secret",
        )

    return x_bot_secret


BotSecretDep = Annotated[str, Depends(verify_bot_secret)]
