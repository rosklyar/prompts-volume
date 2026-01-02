"""API router for reference data accessible by all authenticated users.

Provides read-only access to:
- Topics (grouped by business domain and country)
- Countries
- Business domains
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.admin.models.api_models import (
    BusinessDomainResponse,
    BusinessDomainsListResponse,
    CountriesListResponse,
    CountryResponse,
    TopicResponse,
    TopicsListResponse,
)
from src.auth.deps import get_current_user
from src.database import get_async_session
from src.database.models import BusinessDomain, Country, Topic

router = APIRouter(
    prefix="/api/v1/reference",
    tags=["reference"],
    dependencies=[Depends(get_current_user)],
)

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.get("/business-domains", response_model=BusinessDomainsListResponse)
async def list_business_domains(session: SessionDep):
    """List all business domains for dropdown selection."""
    result = await session.execute(
        select(BusinessDomain).order_by(BusinessDomain.name)
    )
    domains = result.scalars().all()

    return BusinessDomainsListResponse(
        business_domains=[
            BusinessDomainResponse(
                id=d.id,
                name=d.name,
                description=d.description,
            )
            for d in domains
        ]
    )


@router.get("/countries", response_model=CountriesListResponse)
async def list_countries(session: SessionDep):
    """List all countries for dropdown selection."""
    result = await session.execute(select(Country).order_by(Country.name))
    countries = result.scalars().all()

    return CountriesListResponse(
        countries=[
            CountryResponse(
                id=c.id,
                name=c.name,
                iso_code=c.iso_code,
            )
            for c in countries
        ]
    )


@router.get("/topics", response_model=TopicsListResponse)
async def list_topics(
    session: SessionDep,
    business_domain_id: int | None = Query(None, description="Filter by business domain"),
    country_id: int | None = Query(None, description="Filter by country"),
):
    """List topics with optional filtering by business domain and country."""
    query = (
        select(Topic)
        .options(selectinload(Topic.business_domain), selectinload(Topic.country))
        .order_by(Topic.title)
    )

    if business_domain_id is not None:
        query = query.where(Topic.business_domain_id == business_domain_id)
    if country_id is not None:
        query = query.where(Topic.country_id == country_id)

    result = await session.execute(query)
    topics = result.scalars().all()

    return TopicsListResponse(
        topics=[
            TopicResponse(
                id=t.id,
                title=t.title,
                description=t.description,
                business_domain_id=t.business_domain_id,
                business_domain_name=t.business_domain.name,
                country_id=t.country_id,
                country_name=t.country.name,
            )
            for t in topics
        ]
    )
