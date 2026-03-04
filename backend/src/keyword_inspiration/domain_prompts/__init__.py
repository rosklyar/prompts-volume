"""Domain prompt lookup — fetches system_prompt_template from the database."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import BusinessDomain

FALLBACK_TEMPLATE = """You are an expert in creating search prompts for AI assistants in the {domain_name} domain.

CONTEXT:
- Business domain: {domain_name}
- Keywords: {keywords}
- Language: {language}
- Generate exactly 1 prompt per keyword

YOUR TASK:
For each keyword, generate exactly 1 prompt. Choose the most fitting style:
1. Service/solution finding - Questions about where to find services or solutions
2. Information/comparison - Questions comparing options or seeking detailed information
3. Problem-solving - Questions about solving specific problems or achieving goals

CRITICAL INSTRUCTIONS:

1. LANGUAGE: Generate ALL prompts in {language}
   - Match the exact language of the keywords
   - Use natural, native-speaker style

2. STYLE: Keep prompts SHORT and CASUAL (5-15 words typical)
   - Natural, conversational questions
   - Direct and to the point
   - Relevant to {domain_name} domain

3. DOMAIN CONTEXT: Frame prompts within {domain_name}
   - Use domain-specific terminology naturally

4. OUTPUT: Generate exactly 1 prompt per keyword

RESPONSE FORMAT:
Return ONLY valid JSON in this structure:
{{{{
  "prompts": [
    {{{{"prompt": "First prompt text...", "source_keyword": "original keyword"}}}},
    {{{{"prompt": "Second prompt text...", "source_keyword": "original keyword"}}}},
    ...
  ]
}}}}

REMEMBER:
- Exactly 1 prompt per keyword, {keywords_count} prompts total
- All prompts in {language}
- Short, casual, conversational style
- Stay within {domain_name} domain context"""

_TEMPLATE_PLACEHOLDERS = {
    "keywords": "keyword1, keyword2",
    "keywords_count": "2",
    "language": "English",
    "domain_name": "test",
}


def validate_template(template: str) -> None:
    """Validate that a template string contains only known placeholders.

    Raises ValueError if the template contains broken or unknown placeholders.
    """
    try:
        template.format_map(_TEMPLATE_PLACEHOLDERS)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid template placeholder: {exc}") from exc


def _render_template(
    template: str,
    keywords: list[str],
    language: str,
    domain_name: str,
) -> str:
    return template.format_map({
        "keywords": ", ".join(keywords),
        "keywords_count": len(keywords),
        "language": language,
        "domain_name": domain_name,
    })


async def _get_template(session: AsyncSession, domain_name: str) -> str | None:
    result = await session.execute(
        select(BusinessDomain.system_prompt_template).where(
            BusinessDomain.name == domain_name,
            BusinessDomain.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def build_system_prompt(
    session: AsyncSession,
    domain_name: str,
    keywords: list[str],
    language: str,
) -> str:
    template = await _get_template(session, domain_name)
    if template is None:
        template = FALLBACK_TEMPLATE
    return _render_template(template, keywords, language, domain_name)
