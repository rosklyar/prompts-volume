"""Brand variation models for prompt groups."""

from typing import List

from pydantic import BaseModel, Field, field_validator


class BrandVariationModel(BaseModel):
    """Brand with name variations for tracking."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Brand/company name"
    )
    variations: List[str] = Field(
        default_factory=list,
        description="Name variations to detect (case-sensitive)"
    )

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Validate that brand name is not empty or whitespace."""
        if not v.strip():
            raise ValueError("Brand name cannot be empty")
        return v.strip()

    @field_validator("variations")
    @classmethod
    def filter_empty_variations(cls, v: List[str]) -> List[str]:
        """Filter out empty variation strings."""
        return [s.strip() for s in v if s.strip()]
