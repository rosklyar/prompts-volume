"""Pydantic models for admin API endpoints."""

from pydantic import BaseModel, Field


class BusinessDomainResponse(BaseModel):
    """Business domain response model."""

    id: int
    name: str
    description: str


class BusinessDomainsListResponse(BaseModel):
    """List of business domains response."""

    business_domains: list[BusinessDomainResponse]


class CountryResponse(BaseModel):
    """Country response model."""

    id: int
    name: str
    iso_code: str


class CountriesListResponse(BaseModel):
    """List of countries response."""

    countries: list[CountryResponse]


class TopicResponse(BaseModel):
    """Topic response model with related entity names."""

    id: int
    title: str
    description: str
    business_domain_id: int
    business_domain_name: str
    country_id: int
    country_name: str


class TopicsListResponse(BaseModel):
    """List of topics response."""

    topics: list[TopicResponse]


class CreateTopicRequest(BaseModel):
    """Request to create a new topic."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    business_domain_id: int
    country_id: int


class AdminUploadRequest(BaseModel):
    """Request to upload prompts to a topic (admin-specific, topic required)."""

    prompts: list[str] = Field(..., min_length=1)
    selected_indices: list[int] = Field(..., min_length=1)
    topic_id: int  # Required for admin


class AdminUploadResponse(BaseModel):
    """Response after uploading prompts to a topic."""

    total_uploaded: int
    topic_id: int
    topic_title: str
