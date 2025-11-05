import json
import logging
import os
from typing import List
from openai import AsyncOpenAI
from src.prompts.models import GeneratedPrompts, Topic

logger = logging.getLogger(__name__)


class PromptsGeneratorService:
    """Service for generating prompts using OpenAI based on company business information."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize the prompts generator service with OpenAI client."""
        if not api_key:
            raise ValueError("API key is required")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

        logger.info(f"PromptsGeneratorService initialized with model: {self.model}")

    async def generate_prompts(self,
                               topics: list[str],
                               brand_name: str,
                               business_domain: str,
                               country: str,
                               language: str,
                               business_description: str,
                               prompts_per_topic: int = 10
    ) -> GeneratedPrompts:
        """
        Generate prompts_per_topic prompts for each topic based on company business information.

        Args:
            topics: List of topics to generate prompts for
            brand_name: Company brand name (will be avoided in prompts)
            business_domain: Business domain/industry
            country: Target country
            language: Target language for prompts
            business_description: Detailed business description
            prompts_per_topic: Number of prompts to generate per topic (1-50)

        Returns:
            GeneratedPrompts object with topics and their prompts

        Raises:
            ValueError: If validation fails or OpenAI returns invalid response
        """
        # Validate inputs
        if not topics:
            raise ValueError("Topics list cannot be empty")

        if prompts_per_topic < 1 or prompts_per_topic > 50:
            raise ValueError("prompts_per_topic must be between 1 and 50")

        # Create structured prompt for OpenAI
        system_prompt = self._create_system_prompt(
            topics=topics,
            brand_name=brand_name,
            business_domain=business_domain,
            country=country,
            language=language,
            business_description=business_description,
            prompts_per_topic=prompts_per_topic
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate prompts for: {business_description}"}
                ],
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")

            # Parse JSON response
            parsed_data = json.loads(content)

            # Validate and create response
            return self._create_response(parsed_data, topics, prompts_per_topic)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            raise ValueError(f"Invalid JSON response from OpenAI: {e}")
        except Exception as e:
            logger.error(f"Error generating prompts: {e}")
            raise

    def _create_system_prompt(
            self,
            topics: list[str],
            brand_name: str,
            business_domain: str,
            country: str,
            language: str,
            business_description: str,
            prompts_per_topic: int
        ) -> str:
        """Create system prompt for OpenAI to generate structured response."""

        # Add examples section to guide LLM on natural customer question style
        examples_section = f"""
EXAMPLE CUSTOMER QUESTIONS STYLE:
Here are examples of how customers naturally ask questions when looking for products/services (Ukrainian e-commerce examples):

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

Use these examples as inspiration for creating natural, conversational prompts that sound like real customer questions - adapt the style and approach to match the target language and business domain. Create {prompts_per_topic} prompts for each topic in {topics} list
"""

        # Add brand avoidance section
        brand_section = f"""
BRAND STRATEGY:
- DO NOT mention the brand name "{brand_name}" in any generated prompts
- Create generic prompts that customers would use to find solutions in this business area
- Focus on general product/service categories, problems, and comparisons
- Generated prompts should help the company compete by appearing in generic search results
- Use the business description for specificity while avoiding brand mentions
"""

        # Build topics structure for JSON template
        topics_structure = []
        for topic in topics:
            prompts_template = [f'"Prompt {i+1} for {topic} in {language}"' for i in range(prompts_per_topic)]
            topics_structure.append(f'''    {{
      "topic": "{topic}",
      "prompts": [
        {',\n        '.join(prompts_template)}
      ]
    }}''')

        return f"""You are an expert in creating search prompts for AI assistants. Your task is to generate exactly {len(topics)} topics with exactly {prompts_per_topic} prompts each for a company's business.

COMPANY CONTEXT:
- Business Domain: {business_domain}
- Target Country: {country}
- Target Language: {language}
- Business Description: {business_description}
{brand_section}{examples_section}
REQUIREMENTS:
1. Generate prompts for these {len(topics)} topics: {', '.join(topics)}
2. Each topic must have exactly {prompts_per_topic} prompts
3. All prompts must be in {language} language
4. Prompts should represent how potential customers would ask AI assistants to find information about the company
5. Focus on search queries that would lead customers to discover the company's services/products
6. Use the business description to make prompts more specific and relevant to this particular business
7. Generate prompts that sound natural and realistic - like real customer questions
8. Do not generate prompts that directly appeal to or address a specific company (avoid "your company", "you", "your business", etc.) - customers search for generic solutions, not specific companies

RESPONSE FORMAT:
You must respond with valid JSON in this exact structure:

{{
  "topics": [
{',\n'.join(topics_structure)}
  ]
}}

IMPORTANT:
- Return ONLY valid JSON, no additional text
- All text in {language} language
- Prompts should be realistic customer search queries
- Focus on generic queries that customers would use when looking for solutions in this business area"""

    def _create_response(self, parsed_data: dict, expected_topics: list[str], prompts_per_topic: int) -> GeneratedPrompts:
        """
        Create and validate GeneratePromptsResponse from parsed JSON data.

        Args:
            parsed_data: JSON data from OpenAI response
            expected_topics: List of topics that should be in the response
            prompts_per_topic: Expected number of prompts per topic

        Returns:
            GeneratedPrompts object

        Raises:
            ValueError: If response structure is invalid or doesn't match expectations
        """
        topics_data = parsed_data.get("topics", [])

        if not topics_data:
            raise ValueError("Response missing 'topics' field or topics list is empty")

        if len(topics_data) != len(expected_topics):
            raise ValueError(f"Expected {len(expected_topics)} topics, got {len(topics_data)}")

        topics: List[Topic] = []

        for i, topic_data in enumerate(topics_data):
            topic_name = topic_data.get("topic", "")
            prompts = topic_data.get("prompts", [])

            if not topic_name:
                raise ValueError(f"Topic at index {i} is missing 'topic' name")

            if len(prompts) != prompts_per_topic:
                raise ValueError(
                    f"Topic '{topic_name}' has {len(prompts)} prompts, expected {prompts_per_topic}"
                )

            topics.append(Topic(
                topic=topic_name,
                prompts=prompts
            ))

        return GeneratedPrompts(
            topics=topics
        )


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
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        model = os.getenv("PG_OPENAI_MODEL", "gpt-4o-mini")
        _prompts_generator_service = PromptsGeneratorService(api_key=api_key, model=model)
    return _prompts_generator_service
