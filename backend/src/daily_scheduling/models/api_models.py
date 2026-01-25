"""API models for daily scheduling endpoints."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, field_validator, model_validator


# Valid assistant IDs: 1=ChatGPT, 2=Perplexity, 3=Gemini
VALID_ASSISTANT_IDS = {1, 2, 3}


class ScheduleConfigRequest(BaseModel):
    """Request to enable/disable schedule for a group."""

    enabled: bool
    assistant_ids: list[int] | None = None

    @model_validator(mode="after")
    def validate_assistant_ids_required(self) -> Self:
        """Require assistant_ids when enabling schedule."""
        if self.enabled and not self.assistant_ids:
            raise ValueError("assistant_ids required when enabling schedule")
        return self

    @field_validator("assistant_ids")
    @classmethod
    def validate_assistant_ids(cls, v: list[int] | None) -> list[int] | None:
        """Validate assistant IDs."""
        if v is not None:
            if len(v) == 0:
                raise ValueError("At least 1 assistant required")
            invalid = set(v) - VALID_ASSISTANT_IDS
            if invalid:
                raise ValueError(f"Invalid assistant IDs: {invalid}")
            # Remove duplicates while preserving order
            return list(dict.fromkeys(v))
        return v


class ScheduleConfigResponse(BaseModel):
    """Response with current schedule configuration."""

    group_id: int
    enabled: bool
    assistant_ids: list[int] | None  # None when disabled, list when enabled
    last_run_at: datetime | None
