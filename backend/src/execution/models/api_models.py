"""API request/response models for execution endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Status Types
# =============================================================================

# Simplified 3-state status for report generation
PromptStatus = Literal["fresh", "stale", "absent"]


# =============================================================================
# Request Models
# =============================================================================


class RequestFreshExecutionRequest(BaseModel):
    """Request to trigger fresh execution via Bright Data."""

    prompt_ids: list[int] = Field(..., min_length=1, description="Prompt IDs to execute")
    assistant_id: int = Field(
        default=1,
        description="AI Assistant ID to use for execution (default: 1 = ChatGPT)"
    )
    country_id: int = Field(
        ...,
        gt=0,
        description="Country ID for scraping (determines geo-location for results)"
    )


# =============================================================================
# Response Models
# =============================================================================


class QueuedItemInfo(BaseModel):
    """Info about a queued item."""

    prompt_id: int
    status: Literal["queued", "already_pending", "in_progress"]
    estimated_wait: str | None = None


class RequestFreshExecutionResponse(BaseModel):
    """Response after triggering fresh execution via Bright Data."""

    batch_id: str | None  # None if all prompts already pending
    queued_count: int
    already_pending_count: int
    estimated_total_wait: str | None  # None if all prompts already pending
    estimated_completion_at: datetime | None  # None if all prompts already pending
    items: list[QueuedItemInfo]


# =============================================================================
# Report Data Models (Simplified)
# =============================================================================


class PromptReportData(BaseModel):
    """Simplified per-prompt data for report generation UI.

    Uses 3-state status:
    - fresh: latest answer exists and is <=24h old
    - stale: latest answer exists but is >24h old
    - absent: no answer exists
    """

    prompt_id: int
    prompt_text: str

    # Latest evaluation (only one, not a list)
    latest_evaluation_id: int | None
    latest_evaluation_at: datetime | None

    # Simple 3-state status
    status: PromptStatus

    # Queue status (if already requested)
    pending_execution: bool
    estimated_wait: str | None


class ReportDataResponse(BaseModel):
    """Simplified report data for UI."""

    group_id: int
    prompts: list[PromptReportData]

    # Summary counts
    total_prompts: int
    prompts_fresh: int
    prompts_stale: int
    prompts_absent: int

    # Queue info
    prompts_pending_execution: int
    global_queue_size: int

    # Duplicate detection
    would_be_duplicate: bool = False
