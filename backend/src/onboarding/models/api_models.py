"""Pydantic models for onboarding API requests and responses."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from src.prompt_groups.models.brand_models import BrandModel, CompetitorModel


class OnboardingStatusResponse(BaseModel):
    """Response for onboarding status check."""

    is_completed: bool = Field(description="Whether onboarding has been completed")
    is_skipped: bool = Field(description="Whether onboarding was skipped")
    completed_at: Optional[datetime] = Field(
        None, description="Timestamp when onboarding was completed"
    )
    skipped_at: Optional[datetime] = Field(
        None, description="Timestamp when onboarding was skipped"
    )
    has_preferences: bool = Field(
        description="Whether user has any preferences saved"
    )


class UserPreferencesResponse(BaseModel):
    """Response containing user's default preferences."""

    default_country_id: Optional[int] = Field(
        None, description="Default country ID for new groups"
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

    default_country_id: Optional[int] = Field(
        None, description="Default country ID for new groups"
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

    default_country_id: Optional[int] = Field(
        None, description="Default country ID for new groups"
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
