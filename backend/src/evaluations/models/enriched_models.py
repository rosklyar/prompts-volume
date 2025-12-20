"""Enriched evaluation response models."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from src.evaluations.models.brand_models import BrandInputModel, BrandMentionResultModel
from src.evaluations.models.citation_models import CitationLeaderboardModel


class EnrichedEvaluationResultModel(BaseModel):
    """Evaluation result enriched with brand mentions."""

    prompt_id: int = Field(..., description="Prompt ID")
    prompt_text: str = Field(..., description="The prompt text")
    evaluation_id: Optional[int] = Field(None, description="Evaluation record ID")
    status: Optional[str] = Field(None, description="Evaluation status")
    answer: Optional[dict] = Field(None, description="Evaluation answer")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    brand_mentions: Optional[List[BrandMentionResultModel]] = Field(
        None,
        description="Brand mentions detected in response (null if no brands requested)",
    )


class EnrichedResultsRequestModel(BaseModel):
    """Request body for enriched results."""

    brands: Optional[List[BrandInputModel]] = Field(
        None, description="Brands to detect in responses"
    )


class EnrichedResultsResponse(BaseModel):
    """Response with enriched evaluation results."""

    results: List[EnrichedEvaluationResultModel] = Field(
        ..., description="Enriched results"
    )
    citation_leaderboard: CitationLeaderboardModel = Field(
        ..., description="Citation counts aggregated across all results"
    )
