"""Brand and competitor models for prompt groups."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CompanyInfoBase(BaseModel):
    """Base model for company/brand information.

    Shared structure between brands and competitors.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Company/brand name"
    )
    domain: Optional[str] = Field(
        None,
        max_length=255,
        description="Company website domain (e.g., 'example.com')"
    )
    variations: List[str] = Field(
        default_factory=list,
        description="Name variations for detection (case-sensitive)"
    )

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Validate that name is not empty or whitespace."""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize domain format."""
        if v is None:
            return None
        v = v.strip().lower()
        if not v:
            return None
        # Remove protocol if present
        if v.startswith(("http://", "https://")):
            v = v.split("://", 1)[1]
        # Remove trailing slash
        v = v.rstrip("/")
        return v

    @field_validator("variations")
    @classmethod
    def filter_empty_variations(cls, v: List[str]) -> List[str]:
        """Filter out empty variation strings."""
        return [s.strip() for s in v if s.strip()]


class BrandModel(CompanyInfoBase):
    """Brand model for the user's company.

    Inherits all fields from CompanyInfoBase.
    """

    pass


class CompetitorModel(CompanyInfoBase):
    """Competitor model.

    Inherits all fields from CompanyInfoBase.
    """

    pass
