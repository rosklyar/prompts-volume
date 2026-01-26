"""Factory functions for creating brightdata services."""

from functools import cache

from sqlalchemy.ext.asyncio import AsyncSession

from src.brightdata.services.batch_service import BrightDataBatchService
from src.brightdata.services.brightdata_client import BrightDataHttpClient
from src.brightdata.services.brightdata_service import BrightDataService
from src.config.settings import settings


@cache
def get_brightdata_http_client() -> BrightDataHttpClient | None:
    """Singleton HTTP client (stateless, thread-safe)."""
    if not settings.brightdata_api_token:
        return None
    return BrightDataHttpClient(
        api_token=settings.brightdata_api_token,
        base_url=settings.brightdata_base_url,
        timeout=settings.brightdata_timeout,
    )


def create_batch_service(evals_session: AsyncSession) -> BrightDataBatchService:
    """Request-scoped batch service (needs session)."""
    return BrightDataBatchService(evals_session)


def create_brightdata_service(evals_session: AsyncSession) -> BrightDataService:
    """Create BrightData orchestration service."""
    return BrightDataService(
        client=get_brightdata_http_client(),
        batch_service=create_batch_service(evals_session),
        webhook_base_url=settings.backend_webhook_base_url,
        webhook_secret=settings.brightdata_webhook_secret,
    )
