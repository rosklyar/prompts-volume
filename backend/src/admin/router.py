"""API router for admin operations.

Admin-only endpoints for:
- Creating topics
- Uploading prompts to topics
- Approving/rejecting user-submitted prompts

Note: GET endpoints for topics, countries, and business domains have been
moved to the shared reference router (/api/v1/reference/*) for all authenticated users.
Note: Prompt analysis endpoint has been moved to the shared batch router
(/prompts/api/v1/batch/analyze) for all authenticated users.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.models.api_models import (
    AdminUploadRequest,
    AdminUploadResponse,
    CreateTopicRequest,
)
from src.approval.exceptions import ApprovalError, to_http_exception as approval_to_http
from src.approval.models import (
    ApprovalResultResponse,
    ApprovePromptRequest,
    BatchApprovalRequest,
    BatchApprovalResponse,
    PendingPromptResponse,
    PendingPromptsListResponse,
)
from src.approval.service import PromptApprovalService, get_prompt_approval_service
from src.auth.deps import CurrentUser, get_current_active_superuser
from src.database import get_async_session
from src.database.models import Topic
from src.prompts.batch.service import BatchPromptsService, get_batch_prompts_service
from src.reference.models import TopicResponse
from src.topics.exceptions import BusinessDomainNotFoundError, CountryNotFoundError
from src.topics.services.topic_service import TopicServiceDep

router = APIRouter(
    prefix="/admin/api/v1",
    tags=["admin"],
    dependencies=[Depends(get_current_active_superuser)],
)

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
BatchPromptsServiceDep = Annotated[BatchPromptsService, Depends(get_batch_prompts_service)]
ApprovalServiceDep = Annotated[PromptApprovalService, Depends(get_prompt_approval_service)]


@router.post("/topics", response_model=TopicResponse)
async def create_topic(
    request: CreateTopicRequest,
    topic_service: TopicServiceDep,
):
    """Create a new topic."""
    try:
        topic, bd_name, country_name = await topic_service.create_validated(
            request.title,
            request.description,
            request.business_domain_id,
            request.country_id,
        )
    except BusinessDomainNotFoundError:
        raise HTTPException(status_code=404, detail="Business domain not found")
    except CountryNotFoundError:
        raise HTTPException(status_code=404, detail="Country not found")

    return TopicResponse(
        id=topic.id,
        title=topic.title,
        description=topic.description,
        business_domain_id=topic.business_domain_id,
        business_domain_name=bd_name,
        country_id=topic.country_id,
        country_name=country_name,
    )


@router.post("/prompts/upload", response_model=AdminUploadResponse)
async def upload_prompts(
    request: AdminUploadRequest,
    session: SessionDep,
    batch_service: BatchPromptsServiceDep,
):
    """Upload selected prompts and bind to a topic.

    After analyzing prompts with /prompts/analyze, use this endpoint
    to upload only the selected (non-duplicate) prompts.

    Topic ID is required for admin uploads.
    """
    # Verify topic exists
    topic_result = await session.execute(
        select(Topic).where(Topic.id == request.topic_id)
    )
    topic = topic_result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Create prompts via shared service
    try:
        result = await batch_service.create_prompts(
            request.prompts,
            request.selected_indices,
            request.topic_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await session.commit()

    return AdminUploadResponse(
        total_uploaded=result.created_count + result.reused_count,
        topic_id=topic.id,
        topic_title=topic.title,
    )


# --- Prompt Approval Endpoints ---
# Note: Batch routes MUST come before parameterized routes to avoid
# "batch" being parsed as a prompt_id


@router.get("/prompts/pending", response_model=PendingPromptsListResponse)
async def get_pending_prompts(
    approval_service: ApprovalServiceDep,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    topic_id: Optional[int] = Query(None, description="Filter by topic ID"),
):
    """Get prompts awaiting admin approval.

    Returns paginated list of pending prompts with their group context.
    """
    try:
        prompts, total = await approval_service.get_pending_prompts(
            limit=limit,
            offset=offset,
            topic_id=topic_id,
        )
        return PendingPromptsListResponse(
            prompts=[
                PendingPromptResponse(
                    id=p.id,
                    prompt_text=p.prompt_text,
                    topic_id=p.topic_id,
                    topic_title=p.topic_title,
                    user_id=p.user_id,
                    group_ids=p.group_ids,
                    group_titles=p.group_titles,
                )
                for p in prompts
            ],
            total=total,
            limit=limit,
            offset=offset,
        )
    except ApprovalError as e:
        raise approval_to_http(e)


@router.post("/prompts/batch/approve", response_model=BatchApprovalResponse)
async def batch_approve_prompts(
    request: BatchApprovalRequest,
    current_user: CurrentUser,
    approval_service: ApprovalServiceDep,
):
    """Approve multiple prompts at once.

    If any prompts lack a topic, topic_id must be provided.
    """
    try:
        results, failed_ids = await approval_service.batch_approve(
            request.prompt_ids,
            reviewer_id=current_user.id,
            topic_id=request.topic_id,
        )
        return BatchApprovalResponse(
            results=[
                ApprovalResultResponse(
                    prompt_id=r.prompt_id,
                    new_status=r.new_status.value,
                    reviewed_by=r.reviewed_by,
                    reviewed_at=r.reviewed_at,
                )
                for r in results
            ],
            success_count=len(results),
            failed_ids=failed_ids,
        )
    except ApprovalError as e:
        raise approval_to_http(e)


@router.post("/prompts/batch/reject", response_model=BatchApprovalResponse)
async def batch_reject_prompts(
    request: BatchApprovalRequest,
    current_user: CurrentUser,
    approval_service: ApprovalServiceDep,
):
    """Reject multiple prompts at once."""
    try:
        results, failed_ids = await approval_service.batch_reject(
            request.prompt_ids,
            reviewer_id=current_user.id,
        )
        return BatchApprovalResponse(
            results=[
                ApprovalResultResponse(
                    prompt_id=r.prompt_id,
                    new_status=r.new_status.value,
                    reviewed_by=r.reviewed_by,
                    reviewed_at=r.reviewed_at,
                )
                for r in results
            ],
            success_count=len(results),
            failed_ids=failed_ids,
        )
    except ApprovalError as e:
        raise approval_to_http(e)


@router.post("/prompts/{prompt_id}/approve", response_model=ApprovalResultResponse)
async def approve_prompt(
    prompt_id: int,
    current_user: CurrentUser,
    approval_service: ApprovalServiceDep,
    request: Optional[ApprovePromptRequest] = None,
):
    """Approve a pending prompt.

    If the prompt has no topic, topic_id must be provided in the request body.
    """
    try:
        topic_id = request.topic_id if request else None
        result = await approval_service.approve_prompt(
            prompt_id,
            reviewer_id=current_user.id,
            topic_id=topic_id,
        )
        return ApprovalResultResponse(
            prompt_id=result.prompt_id,
            new_status=result.new_status.value,
            reviewed_by=result.reviewed_by,
            reviewed_at=result.reviewed_at,
        )
    except ApprovalError as e:
        raise approval_to_http(e)


@router.post("/prompts/{prompt_id}/reject", response_model=ApprovalResultResponse)
async def reject_prompt(
    prompt_id: int,
    current_user: CurrentUser,
    approval_service: ApprovalServiceDep,
):
    """Reject a pending prompt."""
    try:
        result = await approval_service.reject_prompt(
            prompt_id,
            reviewer_id=current_user.id,
        )
        return ApprovalResultResponse(
            prompt_id=result.prompt_id,
            new_status=result.new_status.value,
            reviewed_by=result.reviewed_by,
            reviewed_at=result.reviewed_at,
        )
    except ApprovalError as e:
        raise approval_to_http(e)
