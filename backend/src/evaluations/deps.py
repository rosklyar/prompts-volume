"""Dependencies for evaluation endpoints."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from src.config.settings import settings


def get_allowed_tokens() -> set[str]:
    """Parse CSV tokens from settings."""
    if not settings.evaluation_api_tokens:
        return set()
    return {t.strip() for t in settings.evaluation_api_tokens.split(",") if t.strip()}


def verify_evaluation_token(
    authorization: str = Header(..., alias="Authorization"),
) -> str:
    """Verify evaluation API token from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = authorization.removeprefix("Bearer ").strip()
    allowed_tokens = get_allowed_tokens()

    if not allowed_tokens:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No evaluation tokens configured",
        )

    if token not in allowed_tokens:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid evaluation token",
        )

    return token


EvaluationTokenDep = Annotated[str, Depends(verify_evaluation_token)]
