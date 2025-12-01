"""Business domain service for database operations."""

from functools import lru_cache
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import BusinessDomain, get_async_session


class BusinessDomainService:
    """Service for managing business domains in the database."""

    def __init__(self, session: AsyncSession):
        """
        Initialize BusinessDomainService with a database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def get_by_name(self, name: str) -> Optional[BusinessDomain]:
        """
        Get a business domain by its name.

        Args:
            name: Business domain name (e.g., 'e-comm')

        Returns:
            BusinessDomain object if found, None otherwise
        """
        result = await self.session.execute(
            select(BusinessDomain).where(BusinessDomain.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, business_domain_id: int) -> Optional[BusinessDomain]:
        """
        Get a business domain by its ID.

        Args:
            business_domain_id: Business domain ID

        Returns:
            BusinessDomain object if found, None otherwise
        """
        result = await self.session.execute(
            select(BusinessDomain).where(BusinessDomain.id == business_domain_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> List[BusinessDomain]:
        """
        Get all business domains from the database.

        Returns:
            List of all BusinessDomain objects
        """
        result = await self.session.execute(
            select(BusinessDomain).order_by(BusinessDomain.name)
        )
        return list(result.scalars().all())

    async def create(self, name: str, description: str) -> BusinessDomain:
        """
        Create a new business domain.

        Args:
            name: Business domain name (e.g., 'e-comm')
            description: Description of the business domain

        Returns:
            Created BusinessDomain object
        """
        business_domain = BusinessDomain(
            name=name,
            description=description,
        )
        self.session.add(business_domain)
        await self.session.flush()
        await self.session.refresh(business_domain)
        return business_domain


@lru_cache()
def get_business_domain_service(
    session: AsyncSession = Depends(get_async_session),
) -> BusinessDomainService:
    """
    Dependency injection function for BusinessDomainService.

    Uses lru_cache to create a singleton instance - the same instance
    is returned on every call, avoiding unnecessary instantiation.

    Args:
        session: AsyncSession injected by FastAPI

    Returns:
        Singleton instance of BusinessDomainService
    """
    return BusinessDomainService(session)
