"""Service for triggering Bright Data batch scraping."""

import logging

from src.brightdata.models.domain import BrightDataPromptInput, BrightDataTriggerRequest
from src.brightdata.services.batch_registry import InMemoryBatchRegistry, get_batch_registry
from src.brightdata.services.brightdata_client import BrightDataHttpClient, get_brightdata_client
from src.config.settings import settings

logger = logging.getLogger(__name__)


class BrightDataService:
    """Service for triggering Bright Data batch scraping.

    Encapsulates all Bright Data triggering logic:
    - Registry management
    - Request building
    - HTTP client calls
    """

    def __init__(
        self,
        client: BrightDataHttpClient | None,
        registry: InMemoryBatchRegistry,
        webhook_base_url: str,
        webhook_secret: str,
        default_country: str,
    ):
        self._client = client
        self._registry = registry
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
        if not self._client:
            logger.debug("Bright Data client not configured, skipping trigger")
            return

        if not prompts:
            logger.debug("No prompts to trigger")
            return

        try:
            # Register batch in memory for webhook correlation
            self._registry.register_batch(batch_id, prompts, user_id)

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


def get_brightdata_service() -> BrightDataService:
    """Dependency injection for BrightDataService."""
    return BrightDataService(
        client=get_brightdata_client(),
        registry=get_batch_registry(),
        webhook_base_url=settings.backend_webhook_base_url,
        webhook_secret=settings.brightdata_webhook_secret,
        default_country=settings.brightdata_default_country,
    )
