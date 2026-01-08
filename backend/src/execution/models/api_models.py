"""API request/response models for execution endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.execution.models.domain import FreshnessCategory


# =============================================================================
# Request Models
# =============================================================================


class RequestFreshExecutionRequest(BaseModel):
    """Request to add prompts to execution queue."""

    prompt_ids: list[int] = Field(..., min_length=1, description="Prompt IDs to queue")


class CancelExecutionRequest(BaseModel):
    """Request to cancel pending executions."""

    prompt_ids: list[int] = Field(..., min_length=1, description="Prompt IDs to cancel")


# =============================================================================
# Response Models
# =============================================================================


class QueuedItemInfo(BaseModel):
    """Info about a queued item."""

    prompt_id: int
    status: Literal["queued", "already_pending", "in_progress"]
    estimated_wait: str | None = None


class RequestFreshExecutionResponse(BaseModel):
    """Response after queuing prompts for execution."""

    batch_id: str
    queued_count: int
    already_pending_count: int
    estimated_total_wait: str
    estimated_completion_at: datetime
    items: list[QueuedItemInfo]


class QueueStatusItem(BaseModel):
    """Status of a single queue item."""

    prompt_id: int
    status: Literal["pending", "in_progress", "completed", "failed", "cancelled"]
    requested_at: datetime
    estimated_wait: str | None = None


class CompletedItemInfo(BaseModel):
    """Info about a completed execution."""

    prompt_id: int
    evaluation_id: int
    completed_at: datetime


class QueueStatusResponse(BaseModel):
    """User's queue status."""

    pending_items: list[QueueStatusItem]
    in_progress_items: list[QueueStatusItem]
    recently_completed: list[CompletedItemInfo]
    total_pending: int
    global_queue_size: int


class CancelExecutionResponse(BaseModel):
    """Response after cancelling executions."""

    cancelled_count: int
    prompt_ids: list[int]


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
