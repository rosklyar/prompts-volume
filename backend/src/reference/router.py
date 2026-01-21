"""API router for reference data accessible by all authenticated users.

Provides read-only access to:
- Topics (grouped by business domain and country)
- Countries
- Business domains
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.auth.deps import get_current_user
from src.businessdomain.services import BusinessDomainService, get_business_domain_service
from src.geography.services import CountryService, get_country_service
from src.reference.models import (
    BusinessDomainResponse,
    BusinessDomainsListResponse,
    CountriesListResponse,
    CountryResponse,
    TopicResponse,
    TopicsListResponse,
)
from src.topics.services.topic_service import TopicServiceDep

router = APIRouter(
    prefix="/api/v1/reference",
    tags=["reference"],
    dependencies=[Depends(get_current_user)],
)

BusinessDomainServiceDep = Annotated[
    BusinessDomainService, Depends(get_business_domain_service)
]
CountryServiceDep = Annotated[CountryService, Depends(get_country_service)]


@router.get("/business-domains", response_model=BusinessDomainsListResponse)
async def list_business_domains(bd_service: BusinessDomainServiceDep):
    """List all business domains for dropdown selection."""
    domains = await bd_service.get_all()

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
async def list_countries(country_service: CountryServiceDep):
    """List all countries for dropdown selection."""
    countries = await country_service.get_all()

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
    topic_service: TopicServiceDep,
    business_domain_id: int | None = Query(None, description="Filter by business domain"),
    country_id: int | None = Query(None, description="Filter by country"),
):
    """List topics with optional filtering by business domain and country."""
    topics = await topic_service.get_all_with_relations(
        business_domain_id=business_domain_id,
        country_id=country_id,
    )

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
