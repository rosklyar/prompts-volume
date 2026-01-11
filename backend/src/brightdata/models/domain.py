"""Internal domain models for Bright Data integration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BrightDataPromptInput:
    """Single prompt input for Bright Data API."""

    url: str  # Always "https://chatgpt.com/"
    prompt: str
    country: str
    web_search: bool = True
    require_sources: bool = False
    additional_prompt: str = ""


@dataclass
class BrightDataTriggerRequest:
    """Request to trigger Bright Data batch."""

    batch_id: str
    inputs: list[BrightDataPromptInput]
    webhook_url: str
    webhook_auth_header: str
