"""Internal domain models for Bright Data integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BrightDataPromptInput:
    """Single prompt input for Bright Data API (legacy format)."""

    url: str
    prompt: str
    country: str
    web_search: bool = True
    require_sources: bool = False
    additional_prompt: str = ""


@dataclass
class BrightDataTriggerRequest:
    """Request to trigger Bright Data batch.

    Inputs are pre-built dicts from strategy.build_input_item().
    """

    batch_id: str
    inputs: list[dict[str, Any]]  # Pre-built by strategy
    webhook_url: str
    webhook_auth_header: str
