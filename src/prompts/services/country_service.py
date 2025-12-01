"""Country service for database operations."""

from functools import lru_cache
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import Country, get_async_session


class CountryService:
    """Service for managing countries in the database."""

    def __init__(self, session: AsyncSession):
        """
        Initialize CountryService with a database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def get_by_iso_code(self, iso_code: str) -> Optional[Country]:
        """
        Get a country by its ISO code.

        Args:
            iso_code: ISO 3166-1 alpha-2 country code (e.g., 'UA', 'US')

        Returns:
            Country object if found, None otherwise
        """
        result = await self.session.execute(
            select(Country).where(Country.iso_code == iso_code.upper())
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, country_id: int) -> Optional[Country]:
        """
        Get a country by its ID.

        Args:
            country_id: Country ID

        Returns:
            Country object if found, None otherwise
        """
        result = await self.session.execute(
            select(Country).where(Country.id == country_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> List[Country]:
        """
        Get all countries from the database.

        Returns:
            List of all Country objects
        """
        result = await self.session.execute(select(Country).order_by(Country.name))
        return list(result.scalars().all())

    async def create(self, name: str, iso_code: str) -> Country:
        """
        Create a new country.

        Args:
            name: Country name (e.g., 'Ukraine')
            iso_code: ISO 3166-1 alpha-2 country code (e.g., 'UA')

        Returns:
            Created Country object
        """
        country = Country(
            name=name,
            iso_code=iso_code.upper(),
        )
        self.session.add(country)
        await self.session.flush()
        await self.session.refresh(country)
        return country


@lru_cache()
def get_country_service(
    session: AsyncSession = Depends(get_async_session),
) -> CountryService:
    """
    Dependency injection function for CountryService.

    Uses lru_cache to create a singleton instance - the same instance
    is returned on every call, avoiding unnecessary instantiation.

    Args:
        session: AsyncSession injected by FastAPI

    Returns:
        Singleton instance of CountryService
    """
    return CountryService(session)
