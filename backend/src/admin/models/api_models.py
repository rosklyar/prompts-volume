"""Pydantic models for admin API endpoints."""

from pydantic import BaseModel, Field


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
