"""Pydantic models for approval API endpoints."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PendingPromptResponse(BaseModel):
    """Response model for a pending prompt in the review queue."""

    id: int
    prompt_text: str
    topic_id: Optional[int]
    topic_title: Optional[str]
    user_id: Optional[str]
    group_ids: List[int]
    group_titles: List[str]

    model_config = {"from_attributes": True}


class PendingPromptsListResponse(BaseModel):
    """Paginated list of pending prompts for admin review."""

    prompts: List[PendingPromptResponse]
    total: int
    limit: int
    offset: int


class ApprovePromptRequest(BaseModel):
    """Request to approve a prompt."""

    topic_id: Optional[int] = Field(
        None,
        description="Required if prompt has no topic. Assigns prompt to this topic.",
    )


class ApprovalResultResponse(BaseModel):
    """Response after approving/rejecting a prompt."""

    prompt_id: int
    new_status: str
    reviewed_by: str
    reviewed_at: datetime


class BatchApprovalRequest(BaseModel):
    """Request to approve/reject multiple prompts."""

    prompt_ids: List[int] = Field(..., min_length=1)
    topic_id: Optional[int] = Field(
        None,
        description="Topic to assign to prompts without topic. Required if any prompt lacks topic.",
    )


class BatchApprovalResponse(BaseModel):
    """Response for batch approval/rejection."""

    results: List[ApprovalResultResponse]
    success_count: int
    failed_ids: List[int] = Field(
        default_factory=list,
        description="IDs of prompts that failed to process",
    )
