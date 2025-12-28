"""Billing services with dependency injection."""

from decimal import Decimal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database.session import get_async_session

from src.billing.services.balance_service import BalanceService
from src.billing.services.consumption_service import ConsumptionService
from src.billing.services.charge_service import ChargeService
from src.billing.services.pricing import FixedPricingStrategy


def get_balance_service(
    session: AsyncSession = Depends(get_async_session),
) -> BalanceService:
    """Dependency injection for BalanceService."""
    return BalanceService(session)


def get_consumption_service(
    session: AsyncSession = Depends(get_async_session),
) -> ConsumptionService:
    """Dependency injection for ConsumptionService."""
    return ConsumptionService(session)


def get_pricing_strategy() -> FixedPricingStrategy:
    """Dependency injection for PricingStrategy."""
    return FixedPricingStrategy(Decimal(str(settings.billing_price_per_evaluation)))


def get_charge_service(
    session: AsyncSession = Depends(get_async_session),
    balance_service: BalanceService = Depends(get_balance_service),
    consumption_service: ConsumptionService = Depends(get_consumption_service),
    pricing_strategy: FixedPricingStrategy = Depends(get_pricing_strategy),
) -> ChargeService:
    """Dependency injection for ChargeService."""
    return ChargeService(
        session=session,
        balance_reader=balance_service,
        balance_modifier=balance_service,
        consumption_tracker=consumption_service,
        pricing_strategy=pricing_strategy,
    )


__all__ = [
    "BalanceService",
    "ConsumptionService",
    "ChargeService",
    "FixedPricingStrategy",
    "get_balance_service",
    "get_consumption_service",
    "get_charge_service",
    "get_pricing_strategy",
]
