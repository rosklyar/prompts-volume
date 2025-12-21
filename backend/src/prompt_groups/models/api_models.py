"""Pydantic models for prompt groups API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from src.prompt_groups.models.brand_models import BrandVariationModel


class CreateGroupRequest(BaseModel):
    """Request to create a new named prompt group."""

    title: str = Field(
        ..., min_length=1, max_length=255, description="Group title (required)"
    )
    brands: Optional[List[BrandVariationModel]] = Field(
        None,
        description="Optional brands to track"
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()

    @field_validator("brands")
    @classmethod
    def validate_unique_brands(cls, v: Optional[List[BrandVariationModel]]) -> Optional[List[BrandVariationModel]]:
        """Ensure brand names are unique within the list."""
        if v and len({b.name for b in v}) != len(v):
            raise ValueError("Brand names must be unique")
        return v


class UpdateGroupRequest(BaseModel):
    """Request to update a prompt group."""

    title: Optional[str] = Field(None, min_length=1, max_length=255, description="New group title")
    brands: Optional[List[BrandVariationModel]] = Field(
        None,
        description="Brands to track (null = no change, [] = clear all brands)"
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip() if v is not None else None

    @field_validator("brands")
    @classmethod
    def validate_unique_brands(cls, v: Optional[List[BrandVariationModel]]) -> Optional[List[BrandVariationModel]]:
        """Ensure brand names are unique within the list."""
        if v and len({b.name for b in v}) != len(v):
            raise ValueError("Brand names must be unique")
        return v


class AddPromptsToGroupRequest(BaseModel):
    """Request to add prompts to a group."""

    prompt_ids: List[int] = Field(
        ..., min_length=1, description="List of prompt IDs to add"
    )


class RemovePromptsFromGroupRequest(BaseModel):
    """Request to remove prompts from a group."""

    prompt_ids: List[int] = Field(
        ..., min_length=1, description="List of prompt IDs to remove"
    )


class PromptInGroupResponse(BaseModel):
    """Response model for a prompt within a group context."""

    binding_id: int
    prompt_id: int
    prompt_text: str
    added_at: datetime

    model_config = {"from_attributes": True}


class GroupSummaryResponse(BaseModel):
    """Summary response for a prompt group (without prompts)."""

    id: int
    title: str
    prompt_count: int
    brand_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroupDetailResponse(BaseModel):
    """Detailed response for a prompt group (with prompts)."""

    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    brands: Optional[List[BrandVariationModel]] = None
    prompts: List[PromptInGroupResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class GroupListResponse(BaseModel):
    """Response containing list of user's groups."""

    groups: List[GroupSummaryResponse]
    total: int


class AddPromptsResultResponse(BaseModel):
    """Response after adding prompts to a group."""

    added_count: int
    skipped_count: int
    bindings: List[PromptInGroupResponse]
