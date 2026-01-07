"""Pydantic API models for evaluations endpoints."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ===== POLL API =====

class PollRequest(BaseModel):
    """Request to poll for a prompt needing evaluation."""

    assistant_name: str = Field(
        ...,
        description="AI assistant name (e.g., 'ChatGPT', 'Claude', 'Perplexity')",
        max_length=100,
    )
    plan_name: str = Field(
        ...,
        description="Assistant plan (e.g., 'Free', 'Plus', 'Max')",
        max_length=100,
    )


class PollResponse(BaseModel):
    """Response with a single claimed prompt (or null if none available)."""

    evaluation_id: Optional[int] = Field(None, description="Evaluation record ID (null if no prompt available)")
    prompt_id: Optional[int] = Field(None, description="Prompt ID")
    prompt_text: Optional[str] = Field(None, description="Prompt text to evaluate")
    topic_id: Optional[int] = Field(None, description="Topic ID")
    claimed_at: Optional[datetime] = Field(None, description="When this evaluation was claimed")


# ===== SUBMIT API =====

class CitationModel(BaseModel):
    """Citation in the answer."""
    url: str = Field(..., description="URL of the citation source")
    text: str = Field(..., description="Citation text/description")


class AnswerModel(BaseModel):
    """Structured answer from AI assistant."""
    response: str = Field(..., description="The main response text")
    citations: List[CitationModel] = Field(..., description="List of citations")
    timestamp: str = Field(..., description="ISO timestamp of when answer was generated")


class SubmitAnswerRequest(BaseModel):
    """Submit evaluation answer."""

    evaluation_id: int = Field(..., description="Evaluation record ID from poll response")
    answer: AnswerModel = Field(..., description="Structured evaluation answer")


class SubmitAnswerResponse(BaseModel):
    """Confirmation of submission."""

    evaluation_id: int = Field(..., description="Evaluation ID")
    prompt_id: int = Field(..., description="Prompt ID")
    status: str = Field(..., description="New status (completed)")
    completed_at: datetime = Field(..., description="Completion timestamp")


# ===== RELEASE API =====

class ReleaseRequest(BaseModel):
    """Release a claimed evaluation."""

    evaluation_id: int = Field(..., description="Evaluation record ID")
    mark_as_failed: bool = Field(
        default=False,
        description="If true, mark as FAILED; if false, delete and make available again"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Reason for failure (required if mark_as_failed=true)"
    )


class ReleaseResponse(BaseModel):
    """Confirmation of release."""

    evaluation_id: int = Field(..., description="Evaluation ID")
    action: str = Field(..., description="Action taken: 'deleted' or 'marked_failed'")


# NOTE: Priority prompts API models have been removed.
# Use POST /execution/api/v1/request-fresh for on-demand execution.
