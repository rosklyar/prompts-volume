"""HTTP client for Bright Data API."""

import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from src.brightdata.models.domain import BrightDataPromptInput, BrightDataTriggerRequest
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
    """

    def __init__(
        self,
        api_token: str,
        dataset_id: str,
        base_url: str = "https://api.brightdata.com/datasets/v3/trigger",
        timeout: float = 30.0,
    ):
        """Initialize Bright Data client.

        Args:
            api_token: Bearer token for API authentication
            dataset_id: Bright Data dataset ID
            base_url: API base URL
            timeout: Request timeout in seconds
        """
        self._api_token = api_token
        self._dataset_id = dataset_id
        self._base_url = base_url
        self._timeout = timeout

    def _build_url(self, request: BrightDataTriggerRequest) -> str:
        """Build trigger URL with query parameters."""
        params = {
            "dataset_id": self._dataset_id,
            "custom_output_fields": ",".join(
                [
                    "prompt",
                    "answer_text",
                    "links_attached",
                    "citations",
                    "shopping",
                    "search_sources",
                    "web_search_query",
                    "input",
                    "timestamp",
                    "model",
                    "recommendations",
                ]
            ),
            "endpoint": request.webhook_url,
            "auth_header": request.webhook_auth_header,
            "notify": "false",
            "format": "json",
            "uncompressed_webhook": "false",
            "force_deliver": "false",
            "include_errors": "true",
        }
        return f"{self._base_url}?{urlencode(params)}"

    def _build_payload(self, inputs: list[BrightDataPromptInput]) -> dict[str, Any]:
        """Build request payload."""
        return {
            "input": [
                {
                    "url": inp.url,
                    "prompt": inp.prompt,
                    "country": inp.country,
                    "web_search": inp.web_search,
                    "require_sources": inp.require_sources,
                    "additional_prompt": inp.additional_prompt,
                }
                for inp in inputs
            ]
        }

    async def trigger_batch(self, request: BrightDataTriggerRequest) -> None:
        """Trigger a batch scraping job (fire-and-forget).

        Args:
            request: Contains prompt inputs and webhook configuration

        Raises:
            BrightDataAPIError: On API failure
        """
        url = self._build_url(request)
        payload = self._build_payload(request.inputs)

        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }

        logger.info(
            f"Triggering Bright Data batch {request.batch_id} "
            f"with {len(request.inputs)} prompts"
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
        dataset_id=settings.brightdata_dataset_id,
        base_url=settings.brightdata_base_url,
        timeout=settings.brightdata_timeout,
    )
