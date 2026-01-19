"""Pydantic models for prompt groups API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from src.prompt_groups.models.brand_models import BrandModel, CompetitorModel


class CreateTopicInput(BaseModel):
    """Input for creating a new topic inline with group."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    business_domain_id: int = Field(..., gt=0)
    country_id: int = Field(..., gt=0)


class TopicInput(BaseModel):
    """Topic selection or creation input.

    Provide at most one of: existing_topic_id OR new_topic.
    If neither provided, group has no topic binding.
    """

    existing_topic_id: Optional[int] = Field(
        None, description="Select existing topic by ID"
    )
    new_topic: Optional[CreateTopicInput] = Field(
        None, description="Create new topic inline (admin only)"
    )

    @model_validator(mode="after")
    def at_most_one_option(self) -> "TopicInput":
        """Ensure at most one of existing_topic_id or new_topic is provided."""
        has_existing = self.existing_topic_id is not None
        has_new = self.new_topic is not None
        if has_existing and has_new:
            raise ValueError("Provide at most one: existing_topic_id OR new_topic")
        return self


class CreateGroupRequest(BaseModel):
    """Request to create a new prompt group."""

    title: str = Field(
        ..., min_length=1, max_length=255, description="Group title (required)"
    )
    topic: Optional[TopicInput] = Field(
        None,
        description="Topic binding (optional, immutable after creation). "
        "If omitted, prompts require admin approval.",
    )
    brand: BrandModel = Field(
        ...,
        description="Brand/company info (required)"
    )
    competitors: Optional[List[CompetitorModel]] = Field(
        None,
        description="Optional list of competitors"
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()

    @field_validator("competitors")
    @classmethod
    def validate_unique_competitor_names(
        cls, v: Optional[List[CompetitorModel]]
    ) -> Optional[List[CompetitorModel]]:
        """Ensure competitor names are unique within the list."""
        if v and len({c.name.lower() for c in v}) != len(v):
            raise ValueError("Competitor names must be unique")
        return v


class UpdateGroupRequest(BaseModel):
    """Request to update a prompt group."""

    title: Optional[str] = Field(
        None, min_length=1, max_length=255, description="New group title"
    )
    brand: Optional[BrandModel] = Field(
        None,
        description="Brand/company info (null = no change)"
    )
    competitors: Optional[List[CompetitorModel]] = Field(
        None,
        description="Competitors list (null = no change, [] = clear)"
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip() if v is not None else None

    @field_validator("competitors")
    @classmethod
    def validate_unique_competitor_names(
        cls, v: Optional[List[CompetitorModel]]
    ) -> Optional[List[CompetitorModel]]:
        """Ensure competitor names are unique within the list."""
        if v and len({c.name.lower() for c in v}) != len(v):
            raise ValueError("Competitor names must be unique")
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
    """Summary response for a prompt group (list view)."""

    id: int
    title: str
    prompt_count: int
    brand_name: str
    competitor_count: int
    topic_id: Optional[int]
    topic_title: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroupDetailResponse(BaseModel):
    """Detailed response for a prompt group."""

    id: int
    title: str
    topic_id: Optional[int]
    topic_title: Optional[str]
    topic_description: Optional[str]
    created_at: datetime
    updated_at: datetime
    brand: BrandModel
    competitors: List[CompetitorModel] = Field(default_factory=list)
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


class AvailablePromptResponse(BaseModel):
    """A prompt available to add to a group."""

    id: int
    prompt_text: str

    model_config = {"from_attributes": True}


class AvailablePromptsListResponse(BaseModel):
    """List of prompts available to add to a group from its topic."""

    prompts: List[AvailablePromptResponse]
    total: int
