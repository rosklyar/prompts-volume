"""Pydantic models for business domain API responses."""

from typing import List, Optional

from pydantic import BaseModel, Field


class DBTopicResponse(BaseModel):
    """DB topic with full metadata."""

    model_config = {"from_attributes": True}

    id: int = Field(..., description="Topic ID from database")
    title: str = Field(..., description="Topic title")
    description: str = Field(..., description="Topic description")
    business_domain_id: int = Field(..., description="Business domain ID")
    country_id: int = Field(..., description="Country ID")


class GeneratedTopicResponse(BaseModel):
    """Generated topic without DB match."""

    title: str = Field(..., description="Generated topic title")
    source: str = Field(default="generated", description="Source indicator")


class TopicsResponse(BaseModel):
    """Topics split into matched DB topics and generated topics."""

    matched_topics: List[DBTopicResponse] = Field(
        ...,
        description="Topics matched from database (can be referenced by ID)"
    )
    unmatched_topics: List[GeneratedTopicResponse] = Field(
        ...,
        description="Topics generated on-the-fly (no DB match)"
    )


class CompanyMetaInfoResponse(BaseModel):
    """Response model for company meta information endpoint."""

    model_config = {"from_attributes": True}

    business_domain: Optional[str] = Field(
        None, description="Business domain name, or null if not classified"
    )
    topics: TopicsResponse = Field(
        ...,
        description="Topics split into matched DB topics and generated topics"
    )
    brand_variations: List[str] = Field(
        ..., description="Brand name variations to filter out from prompts"
    )
