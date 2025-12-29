"""Pydantic models for batch prompts upload API."""

from pydantic import BaseModel, Field, field_validator


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


class BatchAnalyzeResponse(BaseModel):
    """Response containing similarity analysis for all prompts."""

    items: list[BatchPromptAnalysis]
    total_prompts: int
    prompts_with_matches: int
    prompts_without_matches: int


class BatchPromptSelection(BaseModel):
    """User selection for a single prompt in the batch."""

    index: int = Field(..., ge=0)
    use_existing: bool
    selected_prompt_id: int | None = None

    @field_validator("selected_prompt_id")
    @classmethod
    def validate_selection(cls, v: int | None, info) -> int | None:
        """Ensure selected_prompt_id is provided when use_existing is True."""
        use_existing = info.data.get("use_existing")
        if use_existing and v is None:
            raise ValueError(
                "selected_prompt_id is required when use_existing is True"
            )
        return v


class BatchConfirmRequest(BaseModel):
    """Request to confirm batch selections and add prompts to group."""

    selections: list[BatchPromptSelection] = Field(
        ...,
        min_length=1,
        description="User selections for each prompt",
    )
    original_prompts: list[str] = Field(
        ...,
        min_length=1,
        description="Original prompt texts (for creating new prompts)",
    )

    @field_validator("original_prompts")
    @classmethod
    def validate_prompts(cls, v: list[str]) -> list[str]:
        """Validate prompt texts are not empty."""
        for text in v:
            if not text.strip():
                raise ValueError("Prompt text cannot be empty or whitespace")
        return v


class BatchConfirmResponse(BaseModel):
    """Response after confirming batch selections."""

    group_id: int
    bound_existing: int
    created_new: int
    skipped_duplicates: int
    total_processed: int
    prompt_ids: list[int]
