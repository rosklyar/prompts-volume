"""Pydantic API models for Bright Data webhook."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ===== WEBHOOK PAYLOAD MODELS (from Bright Data) =====


class BrightDataCitation(BaseModel):
    """Citation from Bright Data response."""

    url: str
    title: str | None = None
    description: str | None = None
    icon: str | None = None
    domain: str
    cited: bool = False


class BrightDataWebhookItem(BaseModel):
    """Single item in webhook payload from Bright Data.

    Simplified to only include fields we actually use.
    """

    prompt: str
    answer_text: str
    citations: list[BrightDataCitation] | None = None
    links_attached: list[dict[str, Any]] | None = None
    search_sources: list[dict[str, Any]] = Field(default_factory=list)
    country: str | None = None


# ===== RESPONSE MODELS =====


class WebhookResponse(BaseModel):
    """Response to webhook call."""

    status: str
    batch_id: str
    processed_count: int
    failed_count: int
    message: str | None = None
