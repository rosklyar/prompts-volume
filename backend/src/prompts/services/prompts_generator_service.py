import json
import logging
from typing import Dict, List

from openai import AsyncOpenAI

from src.config.settings import settings
from src.topics.services.topic_relevance_filter_service import ClusterWithRelevance
from src.prompts.models import ClusterPrompts, GeneratedPrompts, TopicWithClusters

logger = logging.getLogger(__name__)


class PromptsGeneratorService:
    """Service for generating e-commerce product search prompts based on keyword clusters."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize the prompts generator service with OpenAI client."""
        if not api_key:
            raise ValueError("API key is required")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

        logger.info(f"PromptsGeneratorService initialized with model: {self.model}")

    def _detect_language(self, keywords: List[str]) -> str:
        """
        Detect predominant language in keywords.

        Args:
            keywords: List of keywords to analyze

        Returns:
            Language name ("Ukrainian", "Russian", "English", etc.)
        """
        # Check for Cyrillic characters (Ukrainian/Russian)
        cyrillic_count = 0
        latin_count = 0

        sample_text = " ".join(keywords[:10])  # Sample first 10 keywords

        for char in sample_text:
            if '\u0400' <= char <= '\u04FF':  # Cyrillic range
                cyrillic_count += 1
            elif 'a' <= char.lower() <= 'z':
                latin_count += 1

        if cyrillic_count > latin_count:
            # Detect Ukrainian vs Russian by looking for Ukrainian-specific characters
            ukrainian_chars = ['і', 'ї', 'є', 'ґ', 'І', 'Ї', 'Є', 'Ґ']
            if any(char in sample_text for char in ukrainian_chars):
                return "Ukrainian"
            return "Russian"
        else:
            return "English"

    async def generate_prompts(
        self,
        topics_with_clusters: Dict[str, List[ClusterWithRelevance]],
        number_of_keywords_for_prompt: int = 5
    ) -> GeneratedPrompts:
        """
        Generate e-commerce product search prompts based on keyword clusters.

        For each cluster, generates prompts using groups of keywords. If cluster size > number_of_keywords_for_prompt,
        generates 1 prompt per number_of_keywords_for_prompt keywords.

        Args:
            topics_with_clusters: Dictionary mapping topic name to list of ClusterWithRelevance objects
            number_of_keywords_for_prompt: Number of keywords to use per prompt (default: 5)

        Returns:
            GeneratedPrompts object with topics and cluster prompts

        Raises:
            ValueError: If validation fails or OpenAI returns invalid response
        """
        # Validate inputs
        if not topics_with_clusters:
            raise ValueError("topics_with_clusters cannot be empty")

        if number_of_keywords_for_prompt < 1:
            raise ValueError("number_of_keywords_for_prompt must be at least 1")

        logger.info(
            f"Generating prompts for {len(topics_with_clusters)} topics "
            f"with {number_of_keywords_for_prompt} keywords per prompt"
        )

        # Build results for each topic
        result_topics: List[TopicWithClusters] = []

        for topic_name, clusters in topics_with_clusters.items():
            if not clusters:
                logger.info(f"Skipping topic '{topic_name}' - no clusters")
                continue

            logger.info(f"Processing topic '{topic_name}' with {len(clusters)} clusters")
            cluster_prompts_list: List[ClusterPrompts] = []

            for cluster in clusters:
                # Generate prompts for this cluster
                prompts = await self._generate_prompts_for_cluster(
                    cluster=cluster,
                    topic_name=topic_name,
                    number_of_keywords_for_prompt=number_of_keywords_for_prompt
                )

                cluster_prompts_list.append(ClusterPrompts(
                    cluster_id=cluster.cluster_id,
                    keywords=cluster.keywords,
                    prompts=prompts
                ))

            result_topics.append(TopicWithClusters(
                topic=topic_name,
                clusters=cluster_prompts_list
            ))

        return GeneratedPrompts(topics=result_topics)

    async def _generate_prompts_for_cluster(
        self,
        cluster: ClusterWithRelevance,
        topic_name: str,
        number_of_keywords_for_prompt: int
    ) -> List[str]:
        """
        Generate e-commerce prompts for a single cluster based on keywords.

        If cluster size > number_of_keywords_for_prompt, generates multiple prompts
        (1 prompt per number_of_keywords_for_prompt keywords).

        Args:
            cluster: ClusterWithRelevance object with keywords
            topic_name: Topic this cluster belongs to
            number_of_keywords_for_prompt: Number of keywords to use per prompt

        Returns:
            List of generated prompts
        """
        keywords = cluster.keywords
        num_keywords = len(keywords)
        num_prompts = max(1, num_keywords // number_of_keywords_for_prompt)

        logger.info(
            f"Cluster {cluster.cluster_id} ({topic_name}): "
            f"{num_keywords} keywords -> {num_prompts} prompts"
        )

        # Create system prompt with instructions
        system_prompt = self._create_cluster_system_prompt(
            topic_name=topic_name,
            keywords=keywords,
            num_prompts=num_prompts,
            number_of_keywords_for_prompt=number_of_keywords_for_prompt
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate {num_prompts} e-commerce product search prompts using these keywords: {', '.join(keywords)}"}
                ],
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")

            # Parse JSON response
            parsed_data = json.loads(content)
            prompts = parsed_data.get("prompts", [])

            if not prompts:
                raise ValueError("Response missing 'prompts' field or prompts list is empty")

            return prompts

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            raise ValueError(f"Invalid JSON response from OpenAI: {e}")
        except Exception as e:
            logger.error(f"Error generating prompts for cluster {cluster.cluster_id}: {e}")
            raise

    def _create_cluster_system_prompt(
        self,
        topic_name: str,
        keywords: List[str],
        num_prompts: int,
        number_of_keywords_for_prompt: int
    ) -> str:
        """Create system prompt for generating e-commerce prompts from cluster keywords."""

        # Detect language from keywords
        detected_language = self._detect_language(keywords)

        return f"""You are an expert in creating e-commerce product search prompts for AI assistants.

CONTEXT:
- Topic: {topic_name}
- Keywords from cluster: {', '.join(keywords)}
- Detected language: {detected_language}
- Number of prompts to generate: {num_prompts}
- Keywords per prompt: approximately {number_of_keywords_for_prompt}

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
1. Analyze the keywords - understand the REAL user intent and product needs
2. Generate {num_prompts} SHORT, CASUAL e-commerce prompts
3. Each prompt uses insights from approximately {number_of_keywords_for_prompt} keywords

CRITICAL INSTRUCTIONS:

1. LANGUAGE: Generate ALL prompts in {detected_language}
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
    "Перший короткий промпт...",
    "Другий короткий промпт...",
    ...
  ]
}}

REMEMBER:
- {num_prompts} prompts in {detected_language}
- Short (5-15 words), casual, conversational
- Transform indirect intents to product search prompts
- Follow the Ukrainian examples style"""


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
