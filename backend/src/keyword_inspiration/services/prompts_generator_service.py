import json
import logging
from typing import List

from openai import AsyncOpenAI

from src.config.settings import settings

logger = logging.getLogger(__name__)


class PromptsGeneratorService:
    """Service for generating search prompts based on keywords."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize the prompts generator service with OpenAI client."""
        if not api_key:
            raise ValueError("API key is required")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

        logger.info(f"PromptsGeneratorService initialized with model: {self.model}")

    async def _call_openai_json(
        self,
        system_prompt: str,
        user_prompt: str,
        error_context: str,
    ) -> dict:
        """Make OpenAI API call with JSON response format."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response for {error_context}: {e}")
            raise ValueError(f"Invalid JSON response from OpenAI: {e}")

    async def generate_prompts_from_keywords(
        self,
        keywords: List[str],
        business_domain: str,
        language: str,
    ) -> List[tuple[str, str]]:
        """
        Generate exactly 1 LLM prompt per keyword (max 20 keywords).

        Args:
            keywords: List of keywords to generate prompts from
            business_domain: Business domain (e-comm, fintech, saas, etc.)
            language: Language for generated prompts (e.g., "Ukrainian", "English")

        Returns:
            List of (prompt, source_keyword) tuples

        Raises:
            ValueError: If keywords list is empty
        """
        if not keywords:
            raise ValueError("Keywords list cannot be empty")

        keywords = keywords[:20]

        system_prompt = self._create_keyword_system_prompt(
            keywords, business_domain, language
        )
        user_prompt = (
            f"Generate exactly 1 prompt per keyword. "
            f"Keywords: {', '.join(keywords)}"
        )

        parsed_data = await self._call_openai_json(
            system_prompt, user_prompt, "GSC keywords"
        )
        prompts_data = parsed_data.get("prompts", [])

        if not prompts_data:
            raise ValueError("Response missing 'prompts' field or prompts list is empty")

        return [(item["prompt"], item["source_keyword"]) for item in prompts_data]

    def _create_keyword_system_prompt(
        self,
        keywords: List[str],
        business_domain: str,
        language: str,
    ) -> str:
        """Create system prompt for generating prompts from keywords.

        Uses a rich e-commerce prompt for the 'e-comm' domain and a generic
        domain-aware prompt for everything else.
        """
        if business_domain == "e-comm":
            return self._create_ecomm_system_prompt(keywords, language)

        return self._create_generic_system_prompt(keywords, business_domain, language)

    def _create_ecomm_system_prompt(
        self,
        keywords: List[str],
        language: str,
    ) -> str:
        """Rich e-commerce system prompt with Ukrainian examples and intent mapping."""
        return f"""You are an expert in creating e-commerce product search prompts for AI assistants.

CONTEXT:
- Keywords: {', '.join(keywords)}
- Language: {language}
- Generate exactly 1 prompt per keyword

EXAMPLE STYLE - SHORT AND CASUAL (Ukrainian e-commerce):

Topic: Телевізори
- "Який телевізор краще купити до 10 000 грн?"
- "Телевізор для маленької кімнати – що порадиш?"
- "OLED чи QLED – що вибрати?"
- "Найкращий телевізор для PlayStation 5."

Topic: Смартфони
- "Найкращий смартфон до 15 000 грн."
- "iPhone чи Samsung – що краще у 2025?"
- "Який бюджетний смартфон має хорошу камеру?"
- "Смартфон для ігор до 20 000 грн."

Topic: Побутова техніка
- "Який пилосос купити для квартири?"
- "Робот-пилосос чи звичайний – що краще?"
- "Топ кавоварок для дому."
- "Який блендер обрати для смузі?"

YOUR TASK:
1. Analyze each keyword - understand the REAL user intent and product needs
2. Generate exactly 1 SHORT, CASUAL e-commerce prompt per keyword

CRITICAL INSTRUCTIONS:

1. LANGUAGE: Generate ALL prompts in {language}
   - Match the exact language of the keywords
   - Use natural, native-speaker style

2. STYLE: Keep prompts SHORT and CASUAL (5-15 words typical)
   - Follow the Ukrainian examples style above
   - Natural, conversational questions
   - Direct and to the point
   - Use "–" or "?" for natural breaks

3. INTENT UNDERSTANDING:

   A) DIRECT product searches (keywords like "лучший телефон", "топ ноутбуків"):
      → Create product comparison/recommendation prompts
      → Examples: "Найкращий телефон до 10 000?", "Ноутбук для роботи – що вибрати?"

   B) INDIRECT searches (how-to, tutorials, technical questions):
      → Understand the UNDERLYING PRODUCT NEED
      → Transform to product search prompt

      Examples:
      * Keywords: "як підключити джойстик до телефону", "найкращий телефон для ігор"
        → Prompt: "Який телефон найкращий для ігор з джойстиком?"

      * Keywords: "how to connect bluetooth speaker", "как подключить колонку"
        → Prompt: "Яка блютуз колонка краща до 2000 грн?"

      * Keywords: "печеные яблоки в микроволновке"
        → Prompt: "Яка мікрохвильовка для готування?"

   C) Informational searches (lists, reviews):
      → Create "top/best" or comparison prompts
      → Examples: "Топ-5 смартфонів 2025?", "Які ігри найкращі для телефону?"

RESPONSE FORMAT:
Return ONLY valid JSON in this structure:
{{
  "prompts": [
    {{"prompt": "Short casual prompt...", "source_keyword": "original keyword"}},
    ...
  ]
}}

REMEMBER:
- Exactly 1 prompt per keyword, {len(keywords)} prompts total
- All prompts in {language}
- Short (5-15 words), casual, conversational
- Transform indirect intents to product search prompts
- Follow the Ukrainian examples style"""

    def _create_generic_system_prompt(
        self,
        keywords: List[str],
        business_domain: str,
        language: str,
    ) -> str:
        """Generic domain-aware system prompt for non-e-comm domains."""
        domain_contexts = {
            "general": "products, services, and solutions across various industries",
            "fintech": "financial services, banking, payments, investments, personal finance",
            "saas": "software as a service, business tools, productivity apps, cloud software",
            "education": "learning, courses, training, educational resources, skill development",
            "healthcare": "medical services, health information, wellness, patient care",
            "crypto": "cryptocurrency, blockchain, digital assets, decentralized finance",
            "real-estate": "property, real estate, housing, rentals, property investment",
            "entertainment": "media, streaming, gaming, content, leisure activities",
        }
        domain_context = domain_contexts.get(
            business_domain, f"{business_domain} services and solutions"
        )

        return f"""You are an expert in creating search prompts for AI assistants in the {business_domain} domain.

CONTEXT:
- Business domain: {business_domain} ({domain_context})
- Keywords: {', '.join(keywords)}
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
   - Relevant to {business_domain} domain

3. DOMAIN CONTEXT: Frame prompts within {business_domain}
   - Focus on {domain_context}
   - Use domain-specific terminology naturally

4. OUTPUT: Generate exactly 1 prompt per keyword

RESPONSE FORMAT:
Return ONLY valid JSON in this structure:
{{
  "prompts": [
    {{"prompt": "First prompt text...", "source_keyword": "original keyword"}},
    {{"prompt": "Second prompt text...", "source_keyword": "original keyword"}},
    ...
  ]
}}

REMEMBER:
- Exactly 1 prompt per keyword, {len(keywords)} prompts total
- All prompts in {language}
- Short, casual, conversational style
- Stay within {business_domain} domain context"""


# Global instance for dependency injection
_prompts_generator_service = None


def get_prompts_generator_service() -> PromptsGeneratorService:
    """
    Get the global PromptsGeneratorService instance.
    Creates one if it doesn't exist yet.

    Returns:
        PromptsGeneratorService instance

    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set
    """
    global _prompts_generator_service
    if _prompts_generator_service is None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        _prompts_generator_service = PromptsGeneratorService(
            api_key=settings.openai_api_key,
            model=settings.pg_openai_model
        )
    return _prompts_generator_service
