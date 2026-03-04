"""Pydantic models for admin API endpoints."""

from pydantic import BaseModel, Field, model_validator


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


class UpdateBusinessDomainRequest(BaseModel):
    description: str | None = Field(None, min_length=1)
    system_prompt_template: str | None = Field(None, min_length=1)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "UpdateBusinessDomainRequest":
        if self.description is None and self.system_prompt_template is None:
            raise ValueError("At least one of 'description' or 'system_prompt_template' must be provided")
        return self


class AdminBusinessDomainResponse(BaseModel):
    id: int
    name: str
    description: str
    system_prompt_template: str | None
    is_active: bool


class AdminBusinessDomainsListResponse(BaseModel):
    business_domains: list[AdminBusinessDomainResponse]
