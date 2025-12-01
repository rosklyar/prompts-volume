"""Pydantic models for API requests and responses."""

from typing import List

from pydantic import BaseModel, Field

from src.prompts.models.business_domain import BusinessDomain


class ClusterPrompts(BaseModel):
    """Prompts generated for a specific keyword cluster."""

    cluster_id: int = Field(..., description="Cluster ID")
    keywords: List[str] = Field(..., description="Keywords from cluster used to generate prompts")
    prompts: List[str] = Field(..., description="E-commerce product search prompts for this cluster")


class Topic(BaseModel):
    """Topic with associated cluster prompts."""

    topic: str = Field(..., description="Topic name")
    clusters: List[ClusterPrompts] = Field(..., description="List of cluster prompts for this topic")


class GeneratedPrompts(BaseModel):
    """Complete response with all topics and their cluster prompts."""

    topics: List[Topic] = Field(..., description="List of topics with cluster prompts")


class CompanyMetaInfoResponse(BaseModel):
    """Response model for company meta information endpoint."""

    business_domain: BusinessDomain = Field(..., description="Business domain classification")
    top_topics: List[str] = Field(
        ..., description="Top 10 topics/categories (sales categories for e-commerce)"
    )
    brand_variations: List[str] = Field(
        ..., description="Brand name variations to filter out from prompts"
    )


class GeneratePromptsRequest(BaseModel):
    """Request model for generate prompts endpoint."""

    company_url: str = Field(
        ..., description="Company website URL (e.g., 'moyo.ua', 'https://example.com')"
    )
    iso_country_code: str = Field(
        ..., description="ISO 3166-1 alpha-2 country code (e.g., 'UA', 'US')"
    )
    topics: List[str] = Field(
        ..., min_length=1, description="Selected topics from /meta-info endpoint"
    )
    brand_variations: List[str] = Field(
        ..., min_length=1, description="Selected brand variations from /meta-info endpoint"
    )
