"""Service for Language CRUD operations."""

from typing import List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import Language, get_async_session


class LanguageService:
    """Service for managing Language entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, language_id: int) -> Optional[Language]:
        """Get a language by ID."""
        result = await self.session.execute(
            select(Language).where(Language.id == language_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Language]:
        """Get a language by ISO 639-1 code (e.g., 'uk', 'ru', 'en')."""
        result = await self.session.execute(
            select(Language).where(Language.code == code)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> List[Language]:
        """Get all languages."""
        result = await self.session.execute(select(Language).order_by(Language.name))
        return list(result.scalars().all())

    async def create(self, name: str, code: str) -> Language:
        """Create a new language."""
        language = Language(name=name, code=code)
        self.session.add(language)
        await self.session.flush()
        await self.session.refresh(language)
        return language


def get_language_service(session: AsyncSession = Depends(get_async_session)) -> LanguageService:
    """Dependency injection for LanguageService."""
    return LanguageService(session)
