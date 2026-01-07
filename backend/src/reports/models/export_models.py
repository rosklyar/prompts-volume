"""Pydantic models for report JSON export."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class ExportBrandInfo(BaseModel):
    """Brand information for export."""

    name: str
    domain: Optional[str] = None
    variations: List[str] = Field(default_factory=list)


class ExportBrandConfig(BaseModel):
    """Brand and competitors configuration."""

    brand: Optional[ExportBrandInfo] = None
    competitors: List[ExportBrandInfo] = Field(default_factory=list)


class ExportCitation(BaseModel):
    """Single citation in export."""

    url: str
    text: str = ""


class ExportAnswer(BaseModel):
    """Answer data for export."""

    response: str
    citations: List[ExportCitation] = Field(default_factory=list)


class ExportPromptItem(BaseModel):
    """Single prompt with answer for export."""

    prompt_id: int
    prompt_text: str
    answer: Optional[ExportAnswer] = None
    status: str  # 'included', 'awaiting', 'skipped'


class BrandVisibilityScore(BaseModel):
    """Visibility score for a single brand."""

    brand_name: str
    is_target_brand: bool
    prompts_with_mentions: int
    total_prompts: int
    visibility_percentage: float = Field(ge=0, le=100)


class DomainMentionStat(BaseModel):
    """Domain mention statistics."""

    name: str
    domain: str
    is_target_brand: bool
    total_mentions: int
    prompts_with_mentions: int


class CitationDomainStat(BaseModel):
    """Citation domain count."""

    name: str
    domain: str
    is_target_brand: bool
    citation_count: int


class LeaderboardItem(BaseModel):
    """Single leaderboard entry."""

    path: str
    count: int
    is_domain: bool


class ExportStatistics(BaseModel):
    """All calculated statistics for export."""

    brand_visibility: List[BrandVisibilityScore] = Field(default_factory=list)
    domain_mentions: List[DomainMentionStat] = Field(default_factory=list)
    citation_domains: List[CitationDomainStat] = Field(default_factory=list)
    domain_sources_leaderboard: List[LeaderboardItem] = Field(default_factory=list)
    page_paths_leaderboard: List[LeaderboardItem] = Field(default_factory=list)
    total_citations: int = 0


class ExportReportMeta(BaseModel):
    """Report metadata for export."""

    id: int
    title: Optional[str] = None
    created_at: datetime
    group_id: int
    total_prompts: int
    prompts_with_data: int
    prompts_awaiting: int
    total_cost: Decimal


class ReportJsonExport(BaseModel):
    """Complete JSON export structure."""

    export_version: str = "1.0"
    exported_at: datetime
    report: ExportReportMeta
    brand_info: ExportBrandConfig
    prompts: List[ExportPromptItem]
    statistics: ExportStatistics
