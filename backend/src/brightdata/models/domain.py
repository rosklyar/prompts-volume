"""Internal domain models for Bright Data integration."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class BatchStatus(str, Enum):
    """Status of a Bright Data batch."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


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


@dataclass
class ParsedCitation:
    """A citation extracted from Bright Data response."""

    url: str
    title: str | None
    description: str | None
    domain: str


@dataclass
class ParsedResult:
    """Parsed result from a single Bright Data response item."""

    prompt_id: int
    prompt_text: str
    answer_text: str
    citations: list[ParsedCitation]
    model: str
    timestamp: datetime


@dataclass
class BatchInfo:
    """Info about an in-flight batch."""

    batch_id: str
    user_id: str
    prompt_id_to_text: dict[int, str]
    text_to_prompt_id: dict[str, int]  # Reverse lookup
    created_at: datetime
    status: BatchStatus = BatchStatus.PENDING
    results: list[ParsedResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
