"""API router for admin operations.

Admin-only endpoints for:
- Creating topics
- Analyzing prompts for similarity
- Uploading prompts to topics

Note: GET endpoints for topics, countries, and business domains have been
moved to the shared reference router (/api/v1/reference/*) for all authenticated users.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.admin.models.api_models import (
    AdminUploadRequest,
    AdminUploadResponse,
    CreateTopicRequest,
    TopicResponse,
)
from src.auth.deps import get_current_active_superuser
from src.database import get_async_session
from src.database.models import BusinessDomain, Country, Topic
from src.prompts.batch.models import BatchAnalyzeRequest, BatchAnalyzeResponse
from src.prompts.batch.service import BatchPromptsService, get_batch_prompts_service

router = APIRouter(
    prefix="/admin/api/v1",
    tags=["admin"],
    dependencies=[Depends(get_current_active_superuser)],
)

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]
BatchPromptsServiceDep = Annotated[BatchPromptsService, Depends(get_batch_prompts_service)]


@router.post("/topics", response_model=TopicResponse)
async def create_topic(
    request: CreateTopicRequest,
    session: SessionDep,
):
    """Create a new topic."""
    # Verify business domain exists
    bd_result = await session.execute(
        select(BusinessDomain).where(BusinessDomain.id == request.business_domain_id)
    )
    business_domain = bd_result.scalar_one_or_none()
    if not business_domain:
        raise HTTPException(status_code=404, detail="Business domain not found")

    # Verify country exists
    country_result = await session.execute(
        select(Country).where(Country.id == request.country_id)
    )
    country = country_result.scalar_one_or_none()
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    # Create topic
    topic = Topic(
        title=request.title,
        description=request.description,
        business_domain_id=request.business_domain_id,
        country_id=request.country_id,
    )
    session.add(topic)
    await session.commit()
    await session.refresh(topic)

    return TopicResponse(
        id=topic.id,
        title=topic.title,
        description=topic.description,
        business_domain_id=topic.business_domain_id,
        business_domain_name=business_domain.name,
        country_id=topic.country_id,
        country_name=country.name,
    )


@router.post("/prompts/analyze", response_model=BatchAnalyzeResponse)
async def analyze_prompts(
    request: BatchAnalyzeRequest,
    batch_service: BatchPromptsServiceDep,
):
    """Analyze prompts for similarity matches before uploading.

    For each prompt:
    - Returns top 3 similar prompts if similarity >= 90%
    - Marks as duplicate if similarity >= 99.5%

    Use this endpoint to preview matches before confirming upload.
    """
    try:
        return await batch_service.analyze_batch(request.prompts)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
