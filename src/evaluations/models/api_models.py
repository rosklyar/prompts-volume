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


# ===== RESULTS API =====

class GetResultsRequest(BaseModel):
    """Request to get latest evaluation results for prompts."""

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
    prompt_ids: List[int] = Field(
        ...,
        description="List of prompt IDs to get results for",
    )


class EvaluationResultItem(BaseModel):
    """Single evaluation result."""

    prompt_id: int = Field(..., description="Prompt ID")
    prompt_text: str = Field(..., description="The prompt text")
    evaluation_id: Optional[int] = Field(None, description="Evaluation record ID (null if no evaluation)")
    status: Optional[str] = Field(None, description="Evaluation status (null if no evaluation)")
    answer: Optional[dict] = Field(None, description="Evaluation answer (response, citations, timestamp)")
    completed_at: Optional[datetime] = Field(None, description="When evaluation was completed (null if no evaluation)")


class GetResultsResponse(BaseModel):
    """Response with latest evaluation results."""

    results: List[EvaluationResultItem] = Field(..., description="List of evaluation results")


# ===== PRIORITY PROMPTS API =====

class PriorityPromptItem(BaseModel):
    """Single prompt to add with priority."""
    prompt_text: str = Field(
        ...,
        description="The prompt text to add",
        min_length=1,
        max_length=2000,
    )


class AddPriorityPromptsRequest(BaseModel):
    """Request to add prompts with priority evaluation."""

    prompts: List[PriorityPromptItem] = Field(
        ...,
        description="List of prompts to add",
        min_length=1,
    )
    topic_id: Optional[int] = Field(
        None,
        description="Optional topic ID to associate all prompts with",
    )


class PriorityPromptResult(BaseModel):
    """Result for a single created priority prompt."""
    prompt_id: int = Field(..., description="Prompt ID (new or existing)")
    prompt_text: str = Field(..., description="The prompt text")
    topic_id: Optional[int] = Field(None, description="Assigned topic ID (nullable)")
    was_duplicate: bool = Field(..., description="True if existing prompt was reused")
    similarity_score: Optional[float] = Field(None, description="Similarity score if duplicate")


class AddPriorityPromptsResponse(BaseModel):
    """Response after adding priority prompts."""

    created_count: int = Field(..., description="Number of NEW prompts created")
    reused_count: int = Field(..., description="Number of EXISTING prompts reused")
    total_count: int = Field(..., description="Total prompts in response")
    prompts: List[PriorityPromptResult] = Field(..., description="All prompts (new + reused)")
    request_id: str = Field(..., description="Unique ID for this batch request")
