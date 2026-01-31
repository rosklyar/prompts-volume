"""Pydantic models for GSC API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class GSCAuthInitResponse(BaseModel):
    """Response for auth initiation - contains OAuth URL to redirect user."""

    auth_url: str


class GSCSiteInfo(BaseModel):
    """Information about a GSC property/site."""

    site_url: str
    permission_level: Literal["siteOwner", "siteFullUser", "siteRestrictedUser", "siteUnverifiedUser"]


class GSCConnectionStatus(BaseModel):
    """Status of user's GSC connection."""

    is_connected: bool
    connected_at: datetime | None = None
    sites: list[GSCSiteInfo] | None = None


class GSCDisconnectResponse(BaseModel):
    """Response after disconnecting GSC."""

    message: str


class TokenResponse(BaseModel):
    """OAuth token response from Google."""

    access_token: str
    refresh_token: str | None = None
    expires_in: int
    token_type: str
    scope: str


class SearchAnalyticsRequest(BaseModel):
    """Request for search analytics data."""

    site_url: str
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    row_limit: int = 100


class SearchQueryRow(BaseModel):
    """A single row of search analytics data."""

    keys: list[str]  # Query text (first element is the query)
    clicks: int
    impressions: int
    ctr: float
    position: float


class SearchAnalyticsResponse(BaseModel):
    """Response containing search analytics data."""

    rows: list[SearchQueryRow]


# ===== Onboarding GSC Models =====


class GSCPropertyMatchRequest(BaseModel):
    """Request to match brand domain to GSC property."""

    brand_domain: str


class GSCPropertyMatchResponse(BaseModel):
    """Response from property matching."""

    match_type: Literal["exact", "partial", "multiple", "none"]
    matched_property: str | None
    available_properties: list[GSCSiteInfo]


class GSCKeywordExtractRequest(BaseModel):
    """Request to extract keywords from GSC."""

    site_url: str
    min_word_count: int = 3
    result_limit: int = 10


class GSCKeywordResponse(BaseModel):
    """Single keyword with metrics."""

    query: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class GSCKeywordExtractResponse(BaseModel):
    """Response containing extracted keywords."""

    keywords: list[GSCKeywordResponse]
    total_fetched: int
    total_after_filter: int


class GSCOnboardingCreateRequest(BaseModel):
    """Request to create prompts and group from GSC keywords."""

    keywords: list[str]
    group_title: str
    # Brand/country/competitors passed from frontend (not yet saved to preferences)
    country_id: int
    brand: dict
    competitors: list[dict] | None = None


class GSCOnboardingCreateResponse(BaseModel):
    """Response after creating prompts and group."""

    group_id: int
    group_title: str
    prompts_created: int
    prompt_ids: list[int]
