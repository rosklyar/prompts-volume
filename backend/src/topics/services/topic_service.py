"""Topic service for database operations."""

from typing import Annotated, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.businessdomain.services import BusinessDomainService, get_business_domain_service
from src.database import Topic, get_async_session
from src.geography.services import CountryService, get_country_service
from src.topics.exceptions import BusinessDomainNotFoundError, CountryNotFoundError


class TopicService:
    """Service for managing topics in the database."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        business_domain_service: BusinessDomainService,
        country_service: CountryService,
    ):
        self.session = session
        self._bd_service = business_domain_service
        self._country_service = country_service

    async def get_by_id(self, topic_id: int) -> Optional[Topic]:
        """Get a topic by its ID."""
        result = await self.session.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        return result.scalar_one_or_none()

    async def get_by_country(self, country_id: int) -> List[Topic]:
        """Get all topics for a specific country."""
        result = await self.session.execute(
            select(Topic).where(Topic.country_id == country_id).order_by(Topic.title)
        )
        return list(result.scalars().all())

    async def get_by_business_domain(self, business_domain_id: int) -> List[Topic]:
        """Get all topics for a specific business domain."""
        result = await self.session.execute(
            select(Topic)
            .where(Topic.business_domain_id == business_domain_id)
            .order_by(Topic.title)
        )
        return list(result.scalars().all())

    async def get_by_business_domain_and_country(
        self, business_domain_id: int, country_id: int
    ) -> List[Topic]:
        """Get all topics for specific business domain and country combination."""
        result = await self.session.execute(
            select(Topic)
            .where(
                Topic.business_domain_id == business_domain_id,
                Topic.country_id == country_id,
            )
            .order_by(Topic.title)
        )
        return list(result.scalars().all())

    async def get_all(self) -> List[Topic]:
        """Get all topics from the database."""
        result = await self.session.execute(select(Topic).order_by(Topic.title))
        return list(result.scalars().all())

    async def get_all_with_relations(
        self,
        *,
        business_domain_id: int | None = None,
        country_id: int | None = None,
    ) -> List[Topic]:
        """Get all topics with eager-loaded business_domain and country relations."""
        query = (
            select(Topic)
            .options(selectinload(Topic.business_domain), selectinload(Topic.country))
            .order_by(Topic.title)
        )

        if business_domain_id is not None:
            query = query.where(Topic.business_domain_id == business_domain_id)
        if country_id is not None:
            query = query.where(Topic.country_id == country_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
        title: str,
        description: str,
        business_domain_id: int,
        country_id: int,
    ) -> Topic:
        """Create a new topic without FK validation."""
        topic = Topic(
            title=title,
            description=description,
            business_domain_id=business_domain_id,
            country_id=country_id,
        )
        self.session.add(topic)
        await self.session.flush()
        await self.session.refresh(topic)
        return topic

    async def create_validated(
        self,
        title: str,
        description: str,
        business_domain_id: int,
        country_id: int,
    ) -> tuple[Topic, str, str]:
        """Create topic with FK validation.

        Returns:
            Tuple of (topic, business_domain_name, country_name)

        Raises:
            BusinessDomainNotFoundError: If business domain doesn't exist
            CountryNotFoundError: If country doesn't exist
        """
        bd = await self._bd_service.get_by_id(business_domain_id)
        if bd is None:
            raise BusinessDomainNotFoundError(business_domain_id)

        country = await self._country_service.get_by_id(country_id)
        if country is None:
            raise CountryNotFoundError(country_id)

        topic = await self.create(title, description, business_domain_id, country_id)
        return topic, bd.name, country.name


def get_topic_service(
    session: AsyncSession = Depends(get_async_session),
    bd_service: BusinessDomainService = Depends(get_business_domain_service),
    country_service: CountryService = Depends(get_country_service),
) -> TopicService:
    """Dependency injection function for TopicService."""
    return TopicService(
        session,
        business_domain_service=bd_service,
        country_service=country_service,
    )


TopicServiceDep = Annotated[TopicService, Depends(get_topic_service)]
