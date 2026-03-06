"""Pydantic models for admin API endpoints."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class KeywordFilterEntry(BaseModel):
    """Single predicate entry for keyword filtering config."""

    type: str
    operator: Literal["gt", "gte", "lt", "lte", "eq"] | None = None
    value: int | None = None


class CreateTopicRequest(BaseModel):
    """Request to create a new topic."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    business_domain_id: int
    country_id: int


class AdminUploadRequest(BaseModel):
    """Request to upload prompts to a topic (admin-specific, topic required)."""

    prompts: list[str] = Field(..., min_length=1)
    selected_indices: list[int] = Field(..., min_length=1)
    topic_id: int  # Required for admin


class AdminUploadResponse(BaseModel):
    """Response after uploading prompts to a topic."""

    total_uploaded: int
    topic_id: int
    topic_title: str


# --- Business Domain Admin Models ---


class CreateBusinessDomainRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    system_prompt_template: str = Field(..., min_length=1)
    keyword_filter_config: list[KeywordFilterEntry] | None = None


class UpdateBusinessDomainRequest(BaseModel):
    description: str | None = Field(None, min_length=1)
    system_prompt_template: str | None = Field(None, min_length=1)
    keyword_filter_config: list[KeywordFilterEntry] | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "UpdateBusinessDomainRequest":
        if (
            self.description is None
            and self.system_prompt_template is None
            and self.keyword_filter_config is None
        ):
            raise ValueError(
                "At least one of 'description', 'system_prompt_template', "
                "or 'keyword_filter_config' must be provided"
            )
        return self


class AdminBusinessDomainResponse(BaseModel):
    id: int
    name: str
    description: str
    system_prompt_template: str | None
    keyword_filter_config: list[dict] | None = None
    is_active: bool


class AdminBusinessDomainsListResponse(BaseModel):
    business_domains: list[AdminBusinessDomainResponse]
