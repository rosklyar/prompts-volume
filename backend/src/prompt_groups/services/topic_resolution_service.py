"""Service for resolving topic input to valid topic ID."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import BusinessDomain, Country, Topic
from src.prompt_groups.exceptions import (
    InvalidBusinessDomainError,
    InvalidCountryError,
    TopicNotFoundError,
)
from src.prompt_groups.models.api_models import CreateTopicInput, TopicInput


class TopicResolutionService:
    """Resolves topic input to a valid topic ID.

    Single Responsibility: Topic resolution logic only.
    Handles:
    - Validating existing topic exists
    - Creating new topic with validation
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def resolve(self, topic_input: TopicInput) -> int:
        """Resolve topic input to topic ID.

        Args:
            topic_input: Either existing topic ID or new topic data

        Returns:
            Valid topic ID

        Raises:
            TopicNotFoundError: If existing topic doesn't exist
            InvalidBusinessDomainError: If business domain doesn't exist
            InvalidCountryError: If country doesn't exist
        """
        if topic_input.existing_topic_id is not None:
            return await self._validate_existing(topic_input.existing_topic_id)
        return await self._create_new(topic_input.new_topic)

    async def get_topic(self, topic_id: int) -> Topic:
        """Get topic by ID.

        Raises:
            TopicNotFoundError: If topic doesn't exist
        """
        result = await self._session.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        topic = result.scalar_one_or_none()
        if topic is None:
            raise TopicNotFoundError(topic_id)
        return topic

    async def _validate_existing(self, topic_id: int) -> int:
        """Validate existing topic exists."""
        result = await self._session.execute(
            select(Topic.id).where(Topic.id == topic_id)
        )
        if result.scalar_one_or_none() is None:
            raise TopicNotFoundError(topic_id)
        return topic_id

    async def _create_new(self, data: CreateTopicInput) -> int:
        """Create new topic and return its ID."""
        await self._validate_business_domain(data.business_domain_id)
        await self._validate_country(data.country_id)

        topic = Topic(
            title=data.title,
            description=data.description,
            business_domain_id=data.business_domain_id,
            country_id=data.country_id,
        )
        self._session.add(topic)
        await self._session.flush()
        return topic.id

    async def _validate_business_domain(self, bd_id: int) -> None:
        """Validate business domain exists."""
        result = await self._session.execute(
            select(BusinessDomain.id).where(BusinessDomain.id == bd_id)
        )
        if result.scalar_one_or_none() is None:
            raise InvalidBusinessDomainError(bd_id)

    async def _validate_country(self, country_id: int) -> None:
        """Validate country exists."""
        result = await self._session.execute(
            select(Country.id).where(Country.id == country_id)
        )
        if result.scalar_one_or_none() is None:
            raise InvalidCountryError(country_id)
