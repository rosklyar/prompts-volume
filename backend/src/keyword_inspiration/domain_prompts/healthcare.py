"""Healthcare domain prompt builder."""

from src.keyword_inspiration.domain_prompts._base import GenericDomainPromptBuilder

builder = GenericDomainPromptBuilder(
    domain_name="healthcare",
    domain_context="medical services, health information, wellness, patient care",
)
