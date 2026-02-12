"""Pydantic models for dashboard API endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


PeriodLiteral = Literal["1d", "7d", "30d"]


class CompetitorVisibility(BaseModel):
    """Visibility data for a single competitor/brand."""

    name: str
    domain: str | None
    visibility_percent: float  # 0-100
    is_target_brand: bool
    visibility_change: float | None = None  # delta vs previous report, None if < 2 reports


class SourceStat(BaseModel):
    """Citation domain statistics."""

    domain: str
    citation_count: int
    citation_percent: float  # relative to total citations
    coverage_percent: float  # percentage of answers containing this domain


class PromptGap(BaseModel):
    """A prompt where the target brand is not mentioned."""

    prompt_id: int
    prompt_text: str


class BrandVisibilityPoint(BaseModel):
    """Visibility data for a single brand at a specific point in time."""

    name: str
    domain: str | None
    visibility_percent: float
    is_target_brand: bool


class TimelineDataPoint(BaseModel):
    """A single point on the visibility timeline (one report)."""

    timestamp: datetime
    report_id: int
    brands: list[BrandVisibilityPoint]


class DashboardResponse(BaseModel):
    """Response for the dashboard endpoint."""

    group_id: int
    from_date: datetime
    to_date: datetime
    preset_used: PeriodLiteral | None
    reports_included: int
    assistant_name: str

    # Brand visibility (target brand)
    brand_name: str | None
    brand_domain: str | None = None
    brand_visibility_percent: float  # 0-100

    # All brands/competitors ranked by visibility
    competitors: list[CompetitorVisibility]

    # Citation domains leaderboard
    sources: list[SourceStat]

    # Prompts where target brand is NOT mentioned
    prompt_gaps: list[PromptGap]
    prompt_gaps_count: int

    # Visibility over time (one entry per report, chronological)
    timeline: list[TimelineDataPoint] = []
