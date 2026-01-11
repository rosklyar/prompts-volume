"""API request/response models for execution endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.execution.models.domain import FreshnessCategory


# =============================================================================
# Request Models
# =============================================================================


class RequestFreshExecutionRequest(BaseModel):
    """Request to trigger fresh execution via Bright Data."""

    prompt_ids: list[int] = Field(..., min_length=1, description="Prompt IDs to execute")


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
# Report Data Models
# =============================================================================


class EvaluationOption(BaseModel):
    """An available evaluation (answer) for a prompt."""

    evaluation_id: int
    completed_at: datetime
    is_consumed: bool  # User already paid for this


class PromptReportData(BaseModel):
    """Per-prompt data for report generation UI."""

    prompt_id: int
    prompt_text: str

    # Available evaluations (answers)
    evaluations: list[EvaluationOption]

    # Freshness metadata
    freshness_category: FreshnessCategory
    hours_since_latest: float | None

    # Default selection logic result
    default_evaluation_id: int | None
    show_ask_for_fresh: bool
    auto_ask_for_fresh: bool

    # Queue status (if already requested)
    pending_execution: bool
    estimated_wait: str | None

    # Billing info
    is_consumed: bool  # User already paid for latest evaluation


class ReportDataResponse(BaseModel):
    """Full report data for UI."""

    group_id: int
    prompts: list[PromptReportData]

    # Summary
    total_prompts: int
    prompts_with_data: int
    prompts_fresh: int
    prompts_stale: int
    prompts_very_stale: int
    prompts_no_data: int

    # Queue info
    prompts_pending_execution: int
    global_queue_size: int
