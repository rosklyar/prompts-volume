"""Pydantic models for reports API endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from src.reports.models.brand_models import (
    BrandMentionResultModel,
    DomainMentionResultModel,
)
from src.reports.models.citation_models import CitationLeaderboardModel


# --- Selection-based models for report preview ---


class EvaluationOption(BaseModel):
    """A single evaluation option that can be selected for a prompt."""

    evaluation_id: int
    assistant_plan_id: int
    assistant_plan_name: str
    assistant_name: str
    completed_at: datetime
    is_fresh: bool  # True if user hasn't consumed this evaluation yet
    unit_price: Decimal  # Price if selected (0 if not fresh)


class PromptSelectionInfo(BaseModel):
    """Per-prompt selection information with available options."""

    prompt_id: int
    prompt_text: str
    available_options: List[EvaluationOption]
    default_selection: int | None  # evaluation_id or None if no options
    was_awaiting_in_last_report: bool
    last_report_evaluation_id: int | None
    last_report_evaluation_at: datetime | None
    has_in_progress_evaluation: bool


class PromptSelection(BaseModel):
    """User's selection for a single prompt in report generation."""

    prompt_id: int
    evaluation_id: int | None  # None means skip/awaiting


class SelectiveGenerateReportRequest(BaseModel):
    """Request to generate a report with explicit evaluation selections."""

    title: str | None = None
    selections: List[PromptSelection]
    use_defaults_for_unspecified: bool = True


class SelectableComparisonResponse(BaseModel):
    """Response with selectable evaluation options per prompt."""

    group_id: int
    last_report_at: datetime | None

    # Per-prompt selection data
    prompt_selections: List[PromptSelectionInfo]

    # Summary counts
    total_prompts: int
    prompts_with_options: int  # Prompts that have at least one option
    prompts_awaiting: int  # Prompts with no evaluations at all

    # Brand change detection
    brand_changes: "BrandChangeInfo"

    # Pricing info based on default selections
    default_selection_count: int
    default_fresh_count: int
    default_estimated_cost: Decimal

    # Balance info
    user_balance: Decimal
    price_per_evaluation: Decimal

    # Generation state
    can_generate: bool
    generation_disabled_reason: str | None


# --- Existing models ---


class ReportPreviewResponse(BaseModel):
    """Preview of what a report generation would look like."""

    group_id: int
    total_prompts: int
    prompts_with_data: int
    prompts_awaiting: int
    fresh_evaluations: int
    already_consumed: int
    estimated_cost: Decimal
    user_balance: Decimal
    affordable_count: int
    needs_top_up: bool


class GenerateReportRequest(BaseModel):
    """Request to generate a report."""

    include_previous: bool = True  # Include already-consumed evaluations (free)
    title: str | None = None  # Optional custom title for the report


class ReportItemResponse(BaseModel):
    """A single item in a report."""

    prompt_id: int
    prompt_text: str
    evaluation_id: int | None
    status: str  # 'included', 'awaiting', 'skipped'
    is_fresh: bool
    amount_charged: Decimal | None
    answer: dict | None  # Evaluation answer data if available
    brand_mentions: Optional[List[BrandMentionResultModel]] = None
    domain_mentions: Optional[List[DomainMentionResultModel]] = None


class ReportResponse(BaseModel):
    """Response for a generated report."""

    id: int
    group_id: int
    title: str | None
    created_at: datetime
    total_prompts: int
    prompts_with_data: int
    prompts_awaiting: int
    total_evaluations_loaded: int
    total_cost: Decimal
    items: list[ReportItemResponse]
    citation_leaderboard: Optional[CitationLeaderboardModel] = None


class ReportSummaryResponse(BaseModel):
    """Summary of a report for listing."""

    id: int
    group_id: int
    title: str | None
    created_at: datetime
    total_prompts: int
    prompts_with_data: int
    prompts_awaiting: int
    total_cost: Decimal


class ReportListResponse(BaseModel):
    """List of reports."""

    reports: list[ReportSummaryResponse]
    total: int


class ComparisonResponse(BaseModel):
    """Comparison between current data and last report (deprecated, use EnhancedComparisonResponse)."""

    group_id: int
    last_report_at: datetime | None
    current_prompts_count: int
    current_evaluations_count: int
    new_prompts_added: int
    new_evaluations_available: int
    fresh_data_count: int
    estimated_cost: Decimal
    user_balance: Decimal
    affordable_count: int
    needs_top_up: bool


class PromptFreshnessInfo(BaseModel):
    """Per-prompt freshness information."""

    prompt_id: int
    prompt_text: str
    has_fresher_answer: bool
    latest_answer_at: datetime | None
    previous_answer_at: datetime | None
    next_refresh_estimate: str
    has_in_progress_evaluation: bool


class BrandChangeInfo(BaseModel):
    """Brand/competitors change detection."""

    brand_changed: bool
    competitors_changed: bool
    current_brand: dict | None
    current_competitors: List[dict] | None
    previous_brand: dict | None
    previous_competitors: List[dict] | None


class EnhancedComparisonResponse(BaseModel):
    """Enhanced comparison replacing both /compare and /preview."""

    group_id: int
    last_report_at: datetime | None

    # Current state
    current_prompts_count: int
    current_evaluations_count: int

    # Comparison with last report
    new_prompts_added: int
    prompts_with_fresher_answers: int

    # Per-prompt freshness details
    prompt_freshness: List[PromptFreshnessInfo]

    # Brand change detection
    brand_changes: BrandChangeInfo

    # Cost estimation (merged from preview)
    fresh_evaluations: int
    already_consumed: int
    estimated_cost: Decimal
    user_balance: Decimal
    affordable_count: int
    needs_top_up: bool

    # Generate button state
    can_generate: bool
    generation_disabled_reason: str | None
