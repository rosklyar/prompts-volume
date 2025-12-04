"""Pydantic models for prompt retrieval API responses."""

from typing import List

from pydantic import BaseModel, Field


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
