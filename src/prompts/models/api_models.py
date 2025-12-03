"""Pydantic models for API requests and responses."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer

from src.database import BusinessDomain


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

    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}

    business_domain: Optional[BusinessDomain] = Field(
        None, description="Business domain (serialized as name), or null if not classified"
    )
    topics: TopicsResponse = Field(
        ...,
        description="Topics split into matched DB topics and generated topics"
    )
    brand_variations: List[str] = Field(
        ..., description="Brand name variations to filter out from prompts"
    )

    @field_serializer('business_domain')
    def serialize_business_domain(self, value: Optional[BusinessDomain]) -> Optional[str]:
        """Serialize BusinessDomain ORM object to string name for API response."""
        return value.name if value else None


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


class PromptResponse(BaseModel):
    """Single prompt with ID and text."""

    id: int = Field(..., description="Prompt ID")
    prompt_text: str = Field(..., description="Prompt text")


class TopicPromptsResponse(BaseModel):
    """Prompts for a specific topic."""

    topic_id: int = Field(..., description="Topic ID")
    prompts: List[PromptResponse] = Field(..., description="List of prompts for this topic")


class PromptsListResponse(BaseModel):
    """Response containing prompts grouped by topic."""

    topics: List[TopicPromptsResponse] = Field(..., description="Prompts grouped by topic")
