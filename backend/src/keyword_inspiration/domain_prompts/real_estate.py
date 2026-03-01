"""Real estate domain prompt builder."""

from src.keyword_inspiration.domain_prompts._base import GenericDomainPromptBuilder

builder = GenericDomainPromptBuilder(
    domain_name="real-estate",
    domain_context="property, real estate, housing, rentals, property investment",
)
