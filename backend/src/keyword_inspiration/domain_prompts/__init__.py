"""Domain prompt registry — maps domain name to its prompt builder."""

from src.keyword_inspiration.domain_prompts._base import (
    DomainPromptBuilder,
    GenericDomainPromptBuilder,
)
from src.keyword_inspiration.domain_prompts.crypto import builder as crypto_builder
from src.keyword_inspiration.domain_prompts.ecomm import builder as ecomm_builder
from src.keyword_inspiration.domain_prompts.education import builder as education_builder
from src.keyword_inspiration.domain_prompts.entertainment import (
    builder as entertainment_builder,
)
from src.keyword_inspiration.domain_prompts.fintech import builder as fintech_builder
from src.keyword_inspiration.domain_prompts.general import builder as general_builder
from src.keyword_inspiration.domain_prompts.healthcare import (
    builder as healthcare_builder,
)
from src.keyword_inspiration.domain_prompts.real_estate import (
    builder as real_estate_builder,
)
from src.keyword_inspiration.domain_prompts.saas import builder as saas_builder
from src.keyword_inspiration.domain_prompts.saas_analytics import (
    builder as saas_analytics_builder,
)
from src.keyword_inspiration.domain_prompts.saas_crm import builder as saas_crm_builder
from src.keyword_inspiration.domain_prompts.saas_hr import builder as saas_hr_builder
from src.keyword_inspiration.domain_prompts.saas_marketing import (
    builder as saas_marketing_builder,
)
from src.keyword_inspiration.domain_prompts.saas_pm import builder as saas_pm_builder

PROMPT_REGISTRY: dict[str, DomainPromptBuilder] = {
    "e-comm": ecomm_builder,
    "saas|crm": saas_crm_builder,
    "saas|pm": saas_pm_builder,
    "saas|marketing": saas_marketing_builder,
    "saas|analytics": saas_analytics_builder,
    "saas|hr": saas_hr_builder,
    "fintech": fintech_builder,
    "saas": saas_builder,
    "education": education_builder,
    "healthcare": healthcare_builder,
    "crypto": crypto_builder,
    "real-estate": real_estate_builder,
    "entertainment": entertainment_builder,
    "general": general_builder,
}


def get_prompt_builder(domain_name: str) -> DomainPromptBuilder:
    """Get prompt builder for a domain, falling back to general."""
    return PROMPT_REGISTRY.get(domain_name, PROMPT_REGISTRY["general"])
