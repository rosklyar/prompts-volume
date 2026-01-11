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
    """Single item in webhook payload from Bright Data."""

    # Core fields
    url: str
    prompt: str
    answer_text: str
    model: str | None = None

    # Optional content fields
    answer_text_markdown: str | None = None
    additional_prompt: str | None = None
    additional_answer_text: str | None = None
    response_raw: str | None = None
    answer_section_html: str | None = None

    # Citations and references
    citations: list[BrightDataCitation] | None = None
    links_attached: list[dict[str, Any]] | None = None
    references: list[dict[str, Any]] = Field(default_factory=list)
    search_sources: list[dict[str, Any]] = Field(default_factory=list)

    # Recommendations and shopping
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    shopping: list[dict[str, Any]] = Field(default_factory=list)
    shopping_visible: bool = False

    # Search and map
    web_search_triggered: bool = False
    web_search_query: str | None = None
    is_map: bool = False
    map: dict[str, Any] | None = None

    # Metadata
    country: str | None = None
    index: int | None = None


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
