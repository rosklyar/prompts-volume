"""Pricing strategy protocols."""

from decimal import Decimal
from typing import Protocol


class PricingStrategy(Protocol):
    """Protocol for calculating prices.

    Open/Closed Principle: New pricing strategies (volume discounts,
    subscriptions, promotional pricing) can be added without modifying
    existing code.
    """

    def get_unit_price(self, user_id: str, quantity: int = 1) -> Decimal:
        """Get the price per unit for this user.

        Args:
            user_id: User to price for (allows user-specific pricing)
            quantity: Number of units (allows volume discounts)

        Returns:
            Price per unit as Decimal.
        """
        ...

    def calculate_total(
        self,
        user_id: str,
        quantity: int,
    ) -> Decimal:
        """Calculate total price for quantity units.

        May apply volume discounts or other adjustments.
        """
        ...
