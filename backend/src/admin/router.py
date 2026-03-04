"""API router for admin operations.

Admin-only endpoints for:
- Creating topics
- Uploading prompts to topics
- Approving/rejecting user-submitted prompts
- Hard-deleting users
- Impersonating users
- Onboarding notifications

Note: GET endpoints for topics, countries, and business domains have been
moved to the shared reference router (/api/v1/reference/*) for all authenticated users.
Note: Prompt analysis endpoint has been moved to the shared batch router
(/prompts/api/v1/batch/analyze) for all authenticated users.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.models.api_models import (
    AdminBusinessDomainResponse,
    AdminBusinessDomainsListResponse,
    AdminUploadRequest,
    AdminUploadResponse,
    CreateBusinessDomainRequest,
    CreateTopicRequest,
    UpdateBusinessDomainRequest,
)
from src.admin.models.onboarding_models import (
    OnboardingNotificationsCountResponse,
    OnboardingNotificationsResponse,
    OnboardingUserInfo,
)
from src.admin.user_deletion import (
    CannotDeleteSelfError,
    CannotDeleteSuperuserError,
    UserDeletionResponse,
    UserDeletionServiceDep,
    UserNotFoundError,
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
from src.auth.models import Token
from src.auth.security import create_impersonation_token
from src.database import get_async_session
from src.database.models import BusinessDomain, Country, Topic
from src.database.users_models import User, UserPreferences
from src.database.users_session import get_users_session
from src.businessdomain.services import BusinessDomainService, get_business_domain_service
from src.keyword_inspiration.domain_prompts import FALLBACK_TEMPLATE, validate_template
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
UsersSessionDep = Annotated[AsyncSession, Depends(get_users_session)]
BatchPromptsServiceDep = Annotated[BatchPromptsService, Depends(get_batch_prompts_service)]
ApprovalServiceDep = Annotated[PromptApprovalService, Depends(get_prompt_approval_service)]
BusinessDomainServiceDep = Annotated[BusinessDomainService, Depends(get_business_domain_service)]


# --- Business Domain Admin Endpoints ---
# Note: /default-template MUST be defined before /{domain_id} to avoid path conflict.


@router.get("/business-domains", response_model=AdminBusinessDomainsListResponse)
async def list_business_domains_admin(bd_service: BusinessDomainServiceDep):
    """List all business domains including inactive ones, with templates."""
    domains = await bd_service.get_all(active_only=False)
    return AdminBusinessDomainsListResponse(
        business_domains=[
            AdminBusinessDomainResponse(
                id=d.id,
                name=d.name,
                description=d.description,
                system_prompt_template=d.system_prompt_template,
                is_active=d.is_active,
            )
            for d in domains
        ]
    )


@router.get("/business-domains/default-template")
async def get_default_template():
    """Return the fallback template as a starting point for new domain creation."""
    return {"template": FALLBACK_TEMPLATE}


@router.post(
    "/business-domains",
    response_model=AdminBusinessDomainResponse,
    status_code=201,
)
async def create_business_domain(
    request: CreateBusinessDomainRequest,
    bd_service: BusinessDomainServiceDep,
    session: SessionDep,
):
    """Create a new business domain with a system prompt template."""
    existing = await bd_service.get_by_name(request.name)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Business domain with this name already exists")

    try:
        validate_template(request.system_prompt_template)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    domain = await bd_service.create(
        request.name,
        request.description,
        system_prompt_template=request.system_prompt_template,
    )
    await session.commit()

    return AdminBusinessDomainResponse(
        id=domain.id,
        name=domain.name,
        description=domain.description,
        system_prompt_template=domain.system_prompt_template,
        is_active=domain.is_active,
    )


@router.patch("/business-domains/{domain_id}", response_model=AdminBusinessDomainResponse)
async def update_business_domain(
    domain_id: int,
    request: UpdateBusinessDomainRequest,
    bd_service: BusinessDomainServiceDep,
    session: SessionDep,
):
    """Update a business domain's description and/or system prompt template."""
    if request.system_prompt_template is not None:
        try:
            validate_template(request.system_prompt_template)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    domain = await bd_service.update(
        domain_id,
        description=request.description,
        system_prompt_template=request.system_prompt_template,
    )
    if domain is None:
        raise HTTPException(status_code=404, detail="Business domain not found")

    await session.commit()

    return AdminBusinessDomainResponse(
        id=domain.id,
        name=domain.name,
        description=domain.description,
        system_prompt_template=domain.system_prompt_template,
        is_active=domain.is_active,
    )


@router.delete("/business-domains/{domain_id}", status_code=204)
async def delete_business_domain(
    domain_id: int,
    bd_service: BusinessDomainServiceDep,
    session: SessionDep,
):
    """Soft-delete a business domain (sets is_active=False)."""
    domain = await bd_service.soft_delete(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Business domain not found")
    await session.commit()


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


# --- User Management Endpoints ---


@router.delete("/users/{user_id}/hard-delete", response_model=UserDeletionResponse)
async def hard_delete_user(
    user_id: str,
    current_user: CurrentUser,
    deletion_service: UserDeletionServiceDep,
):
    """Permanently delete a user and all their data.

    This is a hard delete that removes the user record and all associated data
    across all 3 databases:
    - users_db: User, CreditGrant, BalanceTransaction, UserPreferences, OAuthConnection, GSCCredential
    - prompts_db: PromptGroup (cascades bindings), non-approved Prompts (approved are orphaned)
    - evals_db: ConsumedEvaluation, GroupReport, ReportRequest, BrightDataBatch, DailyBatchGroupResult

    PromptEvaluations (answers) are preserved as they're reusable across users.

    Protections:
    - Cannot delete superusers
    - Cannot delete yourself
    """
    try:
        return await deletion_service.hard_delete_user(
            user_id,
            acting_user_id=current_user.id,
        )
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except CannotDeleteSuperuserError:
        raise HTTPException(status_code=403, detail="Cannot delete superuser accounts")
    except CannotDeleteSelfError:
        raise HTTPException(status_code=403, detail="Cannot delete your own account")


# --- Impersonation Endpoints ---


@router.post("/impersonate/{user_id}", response_model=Token)
async def impersonate_user(
    user_id: str,
    current_user: CurrentUser,
    users_session: UsersSessionDep,
):
    """Create an impersonation token for a target user.

    Returns a 1-hour JWT that authenticates as the target user,
    with an `impersonated_by` audit claim.
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot impersonate yourself")

    target = await users_session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot impersonate superuser accounts")

    token = create_impersonation_token(
        target_user_id=target.id,
        admin_user_id=current_user.id,
        expires_delta=timedelta(hours=1),
    )
    return Token(access_token=token)


# --- Onboarding Notifications Endpoints ---


async def _get_onboarding_users(
    users_session: AsyncSession,
    prompts_session: AsyncSession,
    *,
    limit: int,
    offset: int,
) -> tuple[list[OnboardingUserInfo], int]:
    """Query users who completed onboarding but haven't been set up by admin."""
    # Count total
    count_stmt = (
        select(func.count())
        .select_from(UserPreferences)
        .where(
            UserPreferences.onboarding_completed_at.is_not(None),
            UserPreferences.admin_setup_completed_at.is_(None),
        )
    )
    total = (await users_session.execute(count_stmt)).scalar_one()

    if total == 0:
        return [], 0

    # Fetch preferences + user info
    stmt = (
        select(UserPreferences, User)
        .join(User, UserPreferences.user_id == User.id)
        .where(
            UserPreferences.onboarding_completed_at.is_not(None),
            UserPreferences.admin_setup_completed_at.is_(None),
            User.deleted_at.is_(None),
        )
        .order_by(UserPreferences.onboarding_completed_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await users_session.execute(stmt)).all()

    # Collect country/domain IDs for name resolution from prompts_db
    country_ids = {p.default_country_id for p, _ in rows if p.default_country_id}
    domain_ids = {p.default_business_domain_id for p, _ in rows if p.default_business_domain_id}

    country_names: dict[int, str] = {}
    domain_names: dict[int, str] = {}

    if country_ids:
        result = await prompts_session.execute(
            select(Country.id, Country.name).where(Country.id.in_(country_ids))
        )
        country_names = dict(result.all())

    if domain_ids:
        result = await prompts_session.execute(
            select(BusinessDomain.id, BusinessDomain.name).where(
                BusinessDomain.id.in_(domain_ids)
            )
        )
        domain_names = dict(result.all())

    users = [
        OnboardingUserInfo(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            onboarding_completed_at=prefs.onboarding_completed_at,
            default_brand=prefs.default_brand,
            default_competitors=prefs.default_competitors,
            country_name=country_names.get(prefs.default_country_id)
            if prefs.default_country_id
            else None,
            business_domain_name=domain_names.get(prefs.default_business_domain_id)
            if prefs.default_business_domain_id
            else None,
        )
        for prefs, user in rows
    ]

    return users, total


@router.get(
    "/onboarding-notifications",
    response_model=OnboardingNotificationsResponse,
)
async def get_onboarding_notifications(
    users_session: UsersSessionDep,
    prompts_session: SessionDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get users who completed onboarding but haven't been set up by admin."""
    users, total = await _get_onboarding_users(
        users_session, prompts_session, limit=limit, offset=offset
    )
    return OnboardingNotificationsResponse(users=users, total=total)


@router.get(
    "/onboarding-notifications/count",
    response_model=OnboardingNotificationsCountResponse,
)
async def get_onboarding_notifications_count(
    users_session: UsersSessionDep,
):
    """Lightweight count of pending onboarding users (for badge)."""
    stmt = (
        select(func.count())
        .select_from(UserPreferences)
        .join(User, UserPreferences.user_id == User.id)
        .where(
            UserPreferences.onboarding_completed_at.is_not(None),
            UserPreferences.admin_setup_completed_at.is_(None),
            User.deleted_at.is_(None),
        )
    )
    count = (await users_session.execute(stmt)).scalar_one()
    return OnboardingNotificationsCountResponse(count=count)


@router.post("/users/{user_id}/mark-setup")
async def mark_user_setup_complete(
    user_id: str,
    current_user: CurrentUser,
    users_session: UsersSessionDep,
):
    """Mark a user's admin setup as complete."""
    stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
    prefs = (await users_session.execute(stmt)).scalar_one_or_none()

    if not prefs:
        raise HTTPException(status_code=404, detail="User preferences not found")
    if prefs.onboarding_completed_at is None:
        raise HTTPException(status_code=400, detail="User has not completed onboarding")
    if prefs.admin_setup_completed_at is not None:
        raise HTTPException(status_code=400, detail="User setup already completed")

    prefs.admin_setup_completed_at = datetime.now(timezone.utc)
    prefs.admin_setup_by = current_user.id
    return {"message": "User setup marked as complete"}
