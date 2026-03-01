"""General/fallback domain prompt builder."""

from src.keyword_inspiration.domain_prompts._base import GenericDomainPromptBuilder

builder = GenericDomainPromptBuilder(
    domain_name="general",
    domain_context="products, services, and solutions across various industries",
)
