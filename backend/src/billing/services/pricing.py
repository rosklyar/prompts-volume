"""Pricing strategy implementations."""

from decimal import Decimal


class FixedPricingStrategy:
    """Simple fixed price per evaluation.

    Implements PricingStrategy protocol.

    Open for extension: Create new strategy classes for:
    - VolumePricingStrategy
    - SubscriptionPricingStrategy
    - PromotionalPricingStrategy
    """

    def __init__(self, price_per_evaluation: Decimal):
        self._unit_price = price_per_evaluation

    def get_unit_price(self, user_id: str, quantity: int = 1) -> Decimal:
        """Fixed price regardless of user or quantity."""
        return self._unit_price

    def calculate_total(self, user_id: str, quantity: int) -> Decimal:
        """Simple multiplication for fixed pricing."""
        return self._unit_price * quantity


class TieredPricingStrategy:
    """Example of extension: Volume-based tiered pricing.

    Demonstrates Open/Closed Principle - adding new pricing
    without modifying ChargeService.
    """

    def __init__(self, tiers: list[tuple[int, Decimal]]):
        """Initialize tiered pricing.

        Args:
            tiers: List of (threshold, price) tuples.
                   Example: [(0, Decimal("1.0")), (100, Decimal("0.8")), (1000, Decimal("0.5"))]
                   Means: First 100 at $1, next 900 at $0.80, rest at $0.50
        """
        self._tiers = sorted(tiers, key=lambda t: t[0])

    def get_unit_price(self, user_id: str, quantity: int = 1) -> Decimal:
        """Get price for the tier that quantity falls into."""
        for threshold, price in reversed(self._tiers):
            if quantity >= threshold:
                return price
        return self._tiers[0][1] if self._tiers else Decimal("0")

    def calculate_total(self, user_id: str, quantity: int) -> Decimal:
        """Calculate total with tiered pricing."""
        if not self._tiers:
            return Decimal("0")

        total = Decimal("0")
        remaining = quantity
        prev_threshold = 0

        for i, (threshold, price) in enumerate(self._tiers):
            if remaining <= 0:
                break

            # Calculate units in this tier
            if i == len(self._tiers) - 1:
                # Last tier - use all remaining
                units_in_tier = remaining
            else:
                next_threshold = self._tiers[i + 1][0]
                tier_capacity = next_threshold - threshold
                units_in_tier = min(remaining, tier_capacity)

            total += units_in_tier * price
            remaining -= units_in_tier

        return total
