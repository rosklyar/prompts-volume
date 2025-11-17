"""Service for retrieving company metadata (topics and brand variations)."""

from dataclasses import dataclass
from functools import lru_cache
from typing import List


@dataclass
class CompanyMetaInfo:
    """Company metadata for prompts generation."""

    topics: List[str]  # Business topics/categories
    brand_variations: List[str]  # Brand name variations to filter


class CompanyMetaInfoService:
    """
    Service for company metadata.

    Currently returns hardcoded values for MVP.
    TODO: Replace with database/API lookup in production.
    """

    def get_meta_info(self, domain: str) -> CompanyMetaInfo:
        """
        Get company metadata based on domain.

        Args:
            domain: Company domain (e.g., "moyo.ua")

        Returns:
            CompanyMetaInfo with topics and brand variations
        """
        # Hardcoded for Ukrainian e-commerce (works for most sites)
        # TODO: Extract brand variations from domain automatically
        return CompanyMetaInfo(
            topics=[
                "Apple",
                "Смартфони і телефони",
                "Ноутбуки",
                "Планшети",
                "Персональні комп'ютери",
                "Телевізори",
                "Аудіотехніка",
                "Техніка для дому",
                "Техніка для кухні",
                "Ігрові консолі"
            ],
            brand_variations=["moyo", "мойо"]
        )


@lru_cache()
def get_company_meta_info_service() -> CompanyMetaInfoService:
    """Dependency injection for CompanyMetaInfoService."""
    return CompanyMetaInfoService()
