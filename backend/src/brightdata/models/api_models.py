"""Pydantic API models for Bright Data webhook."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.brightdata.models.domain import ParsedCitation


# ===== WEBHOOK PAYLOAD MODELS (from Bright Data) =====


class BrightDataCitation(BaseModel):
    """Citation from Bright Data response."""

    url: str
    title: str | None = None
    description: str | None = None
    icon: str | None = None
    domain: str
    cited: bool = False


class BrightDataInput(BaseModel):
    """Input echoed back in response."""

    url: str
    prompt: str
    country: str
    web_search: bool = True
    require_sources: bool = False
    additional_prompt: str = ""


class BrightDataWebhookItem(BaseModel):
    """Single item in webhook payload."""

    prompt: str
    answer_text: str
    citations: list[BrightDataCitation] | None = None
    links_attached: list[dict[str, Any]] | None = None
    shopping: list[dict[str, Any]] = Field(default_factory=list)
    search_sources: list[dict[str, Any]] = Field(default_factory=list)
    web_search_query: list[str] | None = None
    input: BrightDataInput
    timestamp: datetime
    model: str
    recommendations: list[dict[str, Any]] = Field(default_factory=list)


# ===== RESPONSE MODELS =====


class WebhookResponse(BaseModel):
    """Response to webhook call."""

    status: str
    batch_id: str
    processed_count: int
    failed_count: int
    message: str | None = None


class CitationResponse(BaseModel):
    """Citation in result response."""

    url: str
    title: str | None
    description: str | None
    domain: str

    @classmethod
    def from_parsed(cls, parsed: ParsedCitation) -> CitationResponse:
        """Create from ParsedCitation domain model."""
        return cls(
            url=parsed.url,
            title=parsed.title,
            description=parsed.description,
            domain=parsed.domain,
        )


class ResultResponse(BaseModel):
    """Single result in batch response."""

    prompt_id: int
    prompt_text: str
    answer_text: str
    citations: list[CitationResponse]
    model: str
    timestamp: datetime


class BatchResponse(BaseModel):
    """Batch status and results."""

    batch_id: str
    user_id: str
    status: str
    created_at: datetime
    total_prompts: int
    results: list[ResultResponse]
    errors: list[str]


class AllBatchesResponse(BaseModel):
    """Response containing all batches."""

    batches: list[BatchResponse]
    total_batches: int
