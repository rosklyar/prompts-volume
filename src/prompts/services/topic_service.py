"""Topic service for database operations."""

from functools import lru_cache
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import Topic, get_async_session


class TopicService:
    """Service for managing topics in the database."""

    def __init__(self, session: AsyncSession):
        """
        Initialize TopicService with a database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def get_by_id(self, topic_id: int) -> Optional[Topic]:
        """
        Get a topic by its ID.

        Args:
            topic_id: Topic ID

        Returns:
            Topic object if found, None otherwise
        """
        result = await self.session.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        return result.scalar_one_or_none()

    async def get_by_country(self, country_id: int) -> List[Topic]:
        """
        Get all topics for a specific country.

        Args:
            country_id: Country ID

        Returns:
            List of Topic objects for the country
        """
        result = await self.session.execute(
            select(Topic).where(Topic.country_id == country_id).order_by(Topic.title)
        )
        return list(result.scalars().all())

    async def get_by_business_domain(self, business_domain_id: int) -> List[Topic]:
        """
        Get all topics for a specific business domain.

        Args:
            business_domain_id: Business domain ID

        Returns:
            List of Topic objects for the business domain
        """
        result = await self.session.execute(
            select(Topic)
            .where(Topic.business_domain_id == business_domain_id)
            .order_by(Topic.title)
        )
        return list(result.scalars().all())

    async def get_all(self) -> List[Topic]:
        """
        Get all topics from the database.

        Returns:
            List of all Topic objects
        """
        result = await self.session.execute(select(Topic).order_by(Topic.title))
        return list(result.scalars().all())

    async def create(
        self,
        title: str,
        description: str,
        business_domain_id: int,
        country_id: int,
        embedding: Optional[List[float]] = None,
    ) -> Topic:
        """
        Create a new topic.

        Args:
            title: Topic title
            description: Topic description
            business_domain_id: Business domain ID
            country_id: Country ID
            embedding: Optional vector embedding (384 dimensions)

        Returns:
            Created Topic object
        """
        topic = Topic(
            title=title,
            description=description,
            business_domain_id=business_domain_id,
            country_id=country_id,
            embedding=embedding,
        )
        self.session.add(topic)
        await self.session.flush()
        await self.session.refresh(topic)
        return topic

    async def search_by_embedding(
        self, embedding: List[float], limit: int = 10
    ) -> List[Topic]:
        """
        Search for similar topics using vector similarity (pgvector).

        Args:
            embedding: Query vector (384 dimensions)
            limit: Maximum number of results to return

        Returns:
            List of Topic objects ordered by similarity (most similar first)
        """
        # Use pgvector's <-> operator for cosine distance
        # Lower distance = more similar
        result = await self.session.execute(
            select(Topic)
            .filter(Topic.embedding.isnot(None))
            .order_by(Topic.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        return list(result.scalars().all())


@lru_cache()
def get_topic_service(
    session: AsyncSession = Depends(get_async_session),
) -> TopicService:
    """
    Dependency injection function for TopicService.

    Uses lru_cache to create a singleton instance - the same instance
    is returned on every call, avoiding unnecessary instantiation.

    Args:
        session: AsyncSession injected by FastAPI

    Returns:
        Singleton instance of TopicService
    """
    return TopicService(session)
