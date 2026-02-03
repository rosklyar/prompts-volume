"""Pydantic models for dashboard API endpoints."""

from typing import Literal

from pydantic import BaseModel


PeriodLiteral = Literal["1d", "7d", "30d"]


class CompetitorVisibility(BaseModel):
    """Visibility data for a single competitor/brand."""

    name: str
    domain: str | None
    visibility_percent: float  # 0-100
    is_target_brand: bool


class SourceStat(BaseModel):
    """Citation domain statistics."""

    domain: str
    citation_count: int
    citation_percent: float  # relative to total citations


class PromptGap(BaseModel):
    """A prompt where the target brand is not mentioned."""

    prompt_id: int
    prompt_text: str


class DashboardResponse(BaseModel):
    """Response for the dashboard endpoint."""

    group_id: int
    period: PeriodLiteral
    reports_included: int
    assistant_name: str

    # Brand visibility (target brand)
    brand_name: str | None
    brand_visibility_percent: float  # 0-100

    # All brands/competitors ranked by visibility
    competitors: list[CompetitorVisibility]

    # Citation domains leaderboard
    sources: list[SourceStat]

    # Prompts where target brand is NOT mentioned
    prompt_gaps: list[PromptGap]
    prompt_gaps_count: int
