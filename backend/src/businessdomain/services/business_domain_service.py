"""Business domain service for database operations."""

from typing import List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import BusinessDomain, get_async_session

_UNSET = object()


class BusinessDomainService:
    """Service for managing business domains in the database."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_name(self, name: str) -> Optional[BusinessDomain]:
        result = await self.session.execute(
            select(BusinessDomain).where(BusinessDomain.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, business_domain_id: int) -> Optional[BusinessDomain]:
        result = await self.session.execute(
            select(BusinessDomain).where(BusinessDomain.id == business_domain_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, *, active_only: bool = True) -> List[BusinessDomain]:
        stmt = select(BusinessDomain).order_by(BusinessDomain.name)
        if active_only:
            stmt = stmt.where(BusinessDomain.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        name: str,
        description: str,
        *,
        system_prompt_template: str | None = None,
        keyword_filter_config: list[dict] | None = None,
    ) -> BusinessDomain:
        business_domain = BusinessDomain(
            name=name,
            description=description,
            system_prompt_template=system_prompt_template,
            keyword_filter_config=keyword_filter_config,
        )
        self.session.add(business_domain)
        await self.session.flush()
        await self.session.refresh(business_domain)
        return business_domain

    async def update(
        self,
        domain_id: int,
        *,
        description: str | None = None,
        system_prompt_template: str | None = None,
        keyword_filter_config: list[dict] | None = _UNSET,
    ) -> Optional[BusinessDomain]:
        domain = await self.get_by_id(domain_id)
        if domain is None:
            return None
        if description is not None:
            domain.description = description
        if system_prompt_template is not None:
            domain.system_prompt_template = system_prompt_template
        if keyword_filter_config is not _UNSET:
            domain.keyword_filter_config = keyword_filter_config
        await self.session.flush()
        await self.session.refresh(domain)
        return domain

    async def soft_delete(self, domain_id: int) -> Optional[BusinessDomain]:
        domain = await self.get_by_id(domain_id)
        if domain is None:
            return None
        domain.is_active = False
        await self.session.flush()
        await self.session.refresh(domain)
        return domain


def get_business_domain_service(
    session: AsyncSession = Depends(get_async_session),
) -> BusinessDomainService:
    return BusinessDomainService(session)
