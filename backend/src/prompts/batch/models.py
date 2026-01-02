"""Pydantic models for batch prompts operations."""

from pydantic import BaseModel, Field, field_validator


class SimilarPromptMatch(BaseModel):
    """A similar prompt match from the database."""

    prompt_id: int
    prompt_text: str
    similarity: float = Field(..., ge=0.0, le=1.0)


class BatchPromptAnalysis(BaseModel):
    """Analysis result for a single prompt in the batch."""

    index: int
    input_text: str
    matches: list[SimilarPromptMatch]
    has_matches: bool
    is_duplicate: bool = False  # True if best match >= duplicate_threshold


class BatchAnalyzeRequest(BaseModel):
    """Request to analyze a batch of prompts for similarity matching."""

    prompts: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of prompt texts to analyze (max 100)",
    )

    @field_validator("prompts")
    @classmethod
    def validate_prompts(cls, v: list[str]) -> list[str]:
        """Validate and clean prompt texts."""
        cleaned = []
        for text in v:
            stripped = text.strip()
            if not stripped:
                raise ValueError("Prompt text cannot be empty or whitespace")
            cleaned.append(stripped)
        return cleaned


class BatchAnalyzeResponse(BaseModel):
    """Response containing similarity analysis for all prompts."""

    items: list[BatchPromptAnalysis]
    total_prompts: int
    duplicates_count: int
    with_matches_count: int


class BatchCreateRequest(BaseModel):
    """Request to create new prompts via priority pipeline."""

    prompts: list[str] = Field(..., min_length=1, description="Original prompt texts")
    selected_indices: list[int] = Field(
        ..., min_length=1, description="Indices of prompts to create"
    )
    topic_id: int | None = Field(
        None, description="Optional topic ID to assign to prompts"
    )

    @field_validator("prompts")
    @classmethod
    def validate_prompts(cls, v: list[str]) -> list[str]:
        """Validate prompt texts are not empty."""
        for text in v:
            if not text.strip():
                raise ValueError("Prompt text cannot be empty or whitespace")
        return v

    @field_validator("selected_indices")
    @classmethod
    def validate_indices(cls, v: list[int], info) -> list[int]:
        """Validate indices are non-negative."""
        for idx in v:
            if idx < 0:
                raise ValueError("Index cannot be negative")
        return v


class BatchCreateResponse(BaseModel):
    """Response after creating prompts."""

    created_count: int
    reused_count: int  # Reused due to high similarity at creation
    prompt_ids: list[int]  # IDs of created/reused prompts
    request_id: str  # Priority queue request ID
