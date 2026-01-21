"""HTTP client for Bright Data API."""

import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from src.brightdata.models.domain import BrightDataTriggerRequest
from src.brightdata.strategies.base import AssistantStrategy
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Known error messages for specific status codes
_ERROR_MESSAGES = {
    401: "Authentication failed",
    429: "Rate limit exceeded",
}


class BrightDataAPIError(Exception):
    """Error from Bright Data API."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Bright Data API error {status_code}: {message}")


class BrightDataHttpClient:
    """HTTP client for Bright Data API.

    Uses httpx.AsyncClient for async HTTP calls.
    Strategy-aware: gets dataset_id and output_fields from strategy.
    """

    def __init__(
        self,
        api_token: str,
        base_url: str = "https://api.brightdata.com/datasets/v3/trigger",
        timeout: float = 30.0,
    ):
        """Initialize Bright Data client.

        Args:
            api_token: Bearer token for API authentication
            base_url: API base URL
            timeout: Request timeout in seconds
        """
        self._api_token = api_token
        self._base_url = base_url
        self._timeout = timeout

    def _build_url(
        self,
        request: BrightDataTriggerRequest,
        strategy: AssistantStrategy,
    ) -> str:
        """Build trigger URL with query parameters using strategy config."""
        params = {
            "dataset_id": strategy.get_dataset_id(),
            "custom_output_fields": ",".join(strategy.get_output_fields()),
            "endpoint": request.webhook_url,
            "auth_header": request.webhook_auth_header,
            "notify": "false",
            "format": "json",
            "uncompressed_webhook": "false",
            "force_deliver": "false",
            "include_errors": "true",
        }
        return f"{self._base_url}?{urlencode(params)}"

    def _build_payload(self, inputs: list[dict[str, Any]]) -> dict[str, Any]:
        """Build request payload from pre-built input items."""
        return {"input": inputs}

    async def trigger_batch(
        self,
        request: BrightDataTriggerRequest,
        strategy: AssistantStrategy,
    ) -> None:
        """Trigger a batch scraping job (fire-and-forget).

        Args:
            request: Contains prompt inputs and webhook configuration
            strategy: Assistant strategy for dataset_id and output_fields

        Raises:
            BrightDataAPIError: On API failure
        """
        url = self._build_url(request, strategy)
        payload = self._build_payload(request.inputs)

        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

        logger.info(
            f"Triggering Bright Data batch {request.batch_id} "
            f"with {len(request.inputs)} prompts using {strategy.get_assistant_name()}"
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code >= 400:
                    message = _ERROR_MESSAGES.get(
                        response.status_code, f"API error: {response.text}"
                    )
                    raise BrightDataAPIError(response.status_code, message)

        except httpx.TimeoutException:
            raise BrightDataAPIError(504, "Request timed out")
        except httpx.RequestError as e:
            raise BrightDataAPIError(500, f"Connection error: {str(e)}")


def get_brightdata_client() -> BrightDataHttpClient | None:
    """Get Bright Data client if configured."""
    if not settings.brightdata_api_token:
        return None
    return BrightDataHttpClient(
        api_token=settings.brightdata_api_token,
        base_url=settings.brightdata_base_url,
        timeout=settings.brightdata_timeout,
    )
