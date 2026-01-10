"""Dependencies for Bright Data webhook endpoints."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from src.config.settings import settings


def verify_webhook_auth(
    authorization: str = Header(..., alias="Authorization"),
) -> str:
    """Verify webhook Basic auth header.

    Expects format: "Basic {secret}"
    """
    expected = f"Basic {settings.brightdata_webhook_secret}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook authorization",
        )
    return authorization


WebhookAuthDep = Annotated[str, Depends(verify_webhook_auth)]
