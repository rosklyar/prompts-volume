"""Pydantic models for similar prompts search API."""

from typing import List

from pydantic import BaseModel, Field


class SimilarPromptResponse(BaseModel):
    """Single prompt with similarity score."""

    id: int = Field(..., description="Prompt ID")
    prompt_text: str = Field(..., description="Prompt text")
    similarity: float = Field(..., description="Cosine similarity score (0-1)")


class SimilarPromptsResponse(BaseModel):
    """Response containing similar prompts."""

    query_text: str = Field(..., description="The input text that was searched")
    prompts: List[SimilarPromptResponse] = Field(
        ..., description="Similar prompts sorted by similarity (highest first)"
    )
    total_found: int = Field(..., description="Total number of prompts matching criteria")
