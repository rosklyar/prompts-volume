"""Pydantic models for onboarding API requests and responses."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from src.prompt_groups.models.brand_models import BrandModel, CompetitorModel


# ===== Competitor Discovery API Models =====


class DiscoverCompetitorsRequest(BaseModel):
    """Request to discover competitors using AI."""

    country_id: int = Field(..., gt=0, description="Country ID for localized search")
    business_domain_id: Optional[int] = Field(
        None, description="Business domain ID for context"
    )
    brand: BrandModel = Field(..., description="Brand to find competitors for")


class DiscoveredCompetitorResponse(BaseModel):
    """A discovered competitor with variations."""

    brand_name: str = Field(description="Competitor brand name")
    domain: Optional[str] = Field(None, description="Competitor website domain")
    variations: List[str] = Field(
        default_factory=list, description="Brand name variations for matching"
    )


class DiscoverCompetitorsResponse(BaseModel):
    """Response containing discovered competitors."""

    competitors: List[DiscoveredCompetitorResponse] = Field(
        default_factory=list, description="List of discovered competitors"
    )


# ===== Onboarding Status Models =====


class OnboardingStatusResponse(BaseModel):
    """Response for onboarding status check."""

    is_completed: bool = Field(description="Whether onboarding has been completed")
    completed_at: Optional[datetime] = Field(
        None, description="Timestamp when onboarding was completed"
    )
    has_preferences: bool = Field(
        description="Whether user has any preferences saved"
    )


class UserPreferencesResponse(BaseModel):
    """Response containing user's default preferences."""

    default_country_id: int = Field(
        description="Default country ID for new groups"
    )
    default_business_domain_id: Optional[int] = Field(
        None, description="Default business domain ID for new groups"
    )
    default_brand: Optional[BrandModel] = Field(
        None, description="Default brand for new groups"
    )
    default_competitors: List[CompetitorModel] = Field(
        default_factory=list, description="Default competitors for new groups"
    )
    onboarding_status: OnboardingStatusResponse = Field(
        description="Current onboarding status"
    )


class SavePreferencesRequest(BaseModel):
    """Request to save/update user preferences."""

    default_country_id: int = Field(
        ..., gt=0, description="Default country ID for new groups (REQUIRED)"
    )
    default_business_domain_id: Optional[int] = Field(
        None, description="Default business domain ID for new groups"
    )
    default_brand: BrandModel = Field(
        ..., description="Default brand for new groups"
    )
    default_competitors: Optional[List[CompetitorModel]] = Field(
        None, description="Default competitors for new groups (max 10)"
    )

    @field_validator("default_competitors")
    @classmethod
    def validate_competitors_limit(
        cls, v: Optional[List[CompetitorModel]]
    ) -> Optional[List[CompetitorModel]]:
        """Validate that competitors list doesn't exceed limit."""
        if v is not None and len(v) > 10:
            raise ValueError("Maximum 10 competitors allowed")
        return v


class CompleteOnboardingRequest(BaseModel):
    """Request to complete onboarding with preferences."""

    default_country_id: int = Field(
        ..., gt=0, description="Default country ID for new groups (REQUIRED)"
    )
    default_business_domain_id: Optional[int] = Field(
        None, description="Default business domain ID for new groups"
    )
    default_brand: BrandModel = Field(
        ..., description="Default brand for new groups"
    )
    default_competitors: Optional[List[CompetitorModel]] = Field(
        None, description="Default competitors for new groups (max 10)"
    )

    @field_validator("default_competitors")
    @classmethod
    def validate_competitors_limit(
        cls, v: Optional[List[CompetitorModel]]
    ) -> Optional[List[CompetitorModel]]:
        """Validate that competitors list doesn't exceed limit."""
        if v is not None and len(v) > 10:
            raise ValueError("Maximum 10 competitors allowed")
        return v
