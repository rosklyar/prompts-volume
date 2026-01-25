"""Service for triggering Bright Data batch scraping."""

import logging
import uuid

from src.brightdata.models.domain import BrightDataTriggerRequest
from src.brightdata.services.batch_service import BrightDataBatchService
from src.brightdata.services.brightdata_client import BrightDataHttpClient
from src.brightdata.strategies import AssistantStrategyFactory
from src.config.settings import settings

logger = logging.getLogger(__name__)


def _chunk_dict(d: dict[int, str], chunk_size: int) -> list[dict[int, str]]:
    """Split a dictionary into chunks."""
    items = list(d.items())
    return [dict(items[i:i + chunk_size]) for i in range(0, len(items), chunk_size)]


class BrightDataService:
    """Service for triggering Bright Data batch scraping.

    Encapsulates all Bright Data triggering logic:
    - Batch registration in database
    - Index generation for prompt correlation
    - Request building
    - HTTP client calls
    """

    def __init__(
        self,
        client: BrightDataHttpClient | None,
        batch_service: BrightDataBatchService,
        webhook_base_url: str,
        webhook_secret: str,
    ):
        self._client = client
        self._batch_service = batch_service
        self._webhook_base_url = webhook_base_url
        self._webhook_secret = webhook_secret

    async def trigger_batch(
        self,
        batch_id: str,
        prompts: dict[int, str],
        user_id: str,
        country_id: int,
        country_iso_code: str,
        *,
        assistant_id: int = 1,
    ) -> None:
        """Trigger Bright Data batch with prompts.

        Args:
            batch_id: Unique batch identifier
            prompts: Dict mapping prompt_id to prompt_text
            user_id: User who requested the batch
            country_id: Country ID for database storage
            country_iso_code: ISO country code for BrightData API (e.g., "UA")
            assistant_id: AI assistant ID to scrape (default: 1 = ChatGPT)
        """
        if not prompts:
            logger.debug("No prompts to trigger")
            return

        # Get strategy for the selected assistant
        strategy = AssistantStrategyFactory.get_strategy(assistant_id)
        logger.info(
            f"Using {strategy.get_assistant_name()} "
            f"(dataset: {strategy.get_dataset_id()}) for country={country_iso_code}"
        )

        # Generate index-to-prompt_id mapping (1-based indices, string keys for JSON)
        prompt_ids = list(prompts.keys())
        index_to_prompt_id = {
            str(i + 1): prompt_id
            for i, prompt_id in enumerate(prompt_ids)
        }

        # Register batch in database with index mapping
        await self._batch_service.register_batch(
            batch_id,
            prompt_ids,
            user_id,
            country_id,
            assistant_id=assistant_id,
            index_to_prompt_id=index_to_prompt_id,
        )

        if not self._client:
            logger.debug("Bright Data client not configured, skipping HTTP trigger")
            return

        try:
            # Build request inputs using strategy, with 1-based index for each prompt
            inputs = [
                strategy.build_input_item(
                    prompt=text,
                    country=country_iso_code,
                    index=i + 1,  # 1-based index
                )
                for i, text in enumerate(prompts.values())
            ]

            # Build webhook URL with assistant key for routing
            assistant_key = strategy.get_assistant_key()
            webhook_url = (
                f"{self._webhook_base_url}/evaluations/api/v1/webhook/"
                f"{assistant_key}/{batch_id}"
            )

            trigger_request = BrightDataTriggerRequest(
                batch_id=batch_id,
                inputs=inputs,
                webhook_url=webhook_url,
                webhook_auth_header=f"Basic {self._webhook_secret}",
            )

            await self._client.trigger_batch(trigger_request, strategy)
            logger.info(
                f"Bright Data batch {batch_id} triggered successfully "
                f"for {strategy.get_assistant_name()}, country={country_iso_code}"
            )

        except Exception as e:
            logger.exception(f"Failed to trigger Bright Data batch: {e}")
            raise

    async def trigger_batches_chunked(
        self,
        prompts: dict[int, str],
        user_id: str,
        country_id: int,
        country_iso_code: str,
        *,
        assistant_id: int = 1,
    ) -> list[str]:
        """Trigger BrightData batches with prompts chunked to configured size.

        Args:
            prompts: Dict mapping prompt_id to prompt_text
            user_id: User who requested the batch
            country_id: Country ID for database storage
            country_iso_code: ISO country code for BrightData API (e.g., "UA")
            assistant_id: AI assistant ID to scrape (default: 1 = ChatGPT)

        Returns:
            List of batch IDs created (one per chunk).
        """
        if not prompts:
            return []

        chunks = _chunk_dict(prompts, settings.brightdata_chunk_size)
        batch_ids: list[str] = []

        for chunk in chunks:
            batch_id = str(uuid.uuid4())
            await self.trigger_batch(
                batch_id=batch_id,
                prompts=chunk,
                user_id=user_id,
                country_id=country_id,
                country_iso_code=country_iso_code,
                assistant_id=assistant_id,
            )
            batch_ids.append(batch_id)
            logger.info(
                f"Triggered batch {batch_id} with {len(chunk)} prompts "
                f"for country={country_iso_code}, assistant_id={assistant_id}"
            )

        return batch_ids
