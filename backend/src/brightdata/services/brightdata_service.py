"""Service for triggering Bright Data batch scraping."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.brightdata.models.domain import BrightDataPromptInput, BrightDataTriggerRequest
from src.brightdata.services.batch_service import BrightDataBatchService
from src.brightdata.services.brightdata_client import BrightDataHttpClient

logger = logging.getLogger(__name__)


class BrightDataService:
    """Service for triggering Bright Data batch scraping.

    Encapsulates all Bright Data triggering logic:
    - Batch registration in database
    - Request building
    - HTTP client calls
    """

    def __init__(
        self,
        client: BrightDataHttpClient | None,
        batch_service: BrightDataBatchService,
        webhook_base_url: str,
        webhook_secret: str,
        default_country: str,
    ):
        self._client = client
        self._batch_service = batch_service
        self._webhook_base_url = webhook_base_url
        self._webhook_secret = webhook_secret
        self._default_country = default_country

    async def trigger_batch(
        self,
        batch_id: str,
        prompts: dict[int, str],
        user_id: str,
    ) -> None:
        """Trigger Bright Data batch with prompts.

        Args:
            batch_id: Unique batch identifier
            prompts: Dict mapping prompt_id to prompt_text
            user_id: User who requested the batch
        """
        if not prompts:
            logger.debug("No prompts to trigger")
            return

        # Always register batch in database (for webhook correlation and pending tracking)
        prompt_ids = list(prompts.keys())
        await self._batch_service.register_batch(batch_id, prompt_ids, user_id)

        if not self._client:
            logger.debug("Bright Data client not configured, skipping HTTP trigger")
            return

        try:

            # Build request inputs
            inputs = [
                BrightDataPromptInput(
                    url="https://chatgpt.com/",
                    prompt=text,
                    country=self._default_country,
                )
                for text in prompts.values()
            ]

            webhook_url = f"{self._webhook_base_url}/evaluations/api/v1/webhook/{batch_id}"

            trigger_request = BrightDataTriggerRequest(
                batch_id=batch_id,
                inputs=inputs,
                webhook_url=webhook_url,
                webhook_auth_header=f"Basic {self._webhook_secret}",
            )

            await self._client.trigger_batch(trigger_request)
            logger.info(f"Bright Data batch {batch_id} triggered successfully")

        except Exception as e:
            logger.exception(f"Failed to trigger Bright Data batch: {e}")
            raise


def get_brightdata_service(evals_session: AsyncSession) -> BrightDataService:
    """Create BrightDataService with database session.

    Note: This is NOT a FastAPI dependency - it creates the service
    with an existing session. Use in endpoints that already have sessions.
    """
    from src.brightdata.services.brightdata_client import get_brightdata_client
    from src.config.settings import settings

    return BrightDataService(
        client=get_brightdata_client(),
        batch_service=BrightDataBatchService(evals_session),
        webhook_base_url=settings.backend_webhook_base_url,
        webhook_secret=settings.brightdata_webhook_secret,
        default_country=settings.brightdata_default_country,
    )
