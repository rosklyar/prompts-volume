"""Service for providing topics by matching LLM-generated topics with DB topics."""

import json
import logging
import os
from typing import List

import numpy as np
from fastapi import Depends
from openai import AsyncOpenAI
from sklearn.metrics.pairwise import cosine_similarity

from src.database import BusinessDomain, Country, Topic
from src.embeddings.embeddings_service import EmbeddingsService, get_embeddings_service
from src.prompts.models.generated_topic import GeneratedTopic
from src.prompts.models.topic_match_result import TopicMatchResult
from src.prompts.services.topic_service import TopicService, get_topic_service

logger = logging.getLogger(__name__)


class TopicsProvider:
    """Provides topics by matching LLM-generated topics with existing DB topics."""

    def __init__(
        self,
        api_key: str,
        model: str,
        topic_service: TopicService,
        embeddings_service: EmbeddingsService
    ):
        if not api_key:
            raise ValueError("API key is required")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.topic_service = topic_service
        self.embeddings_service = embeddings_service

    async def provide(
        self,
        domain: str,
        business_domain: BusinessDomain,
        country: Country
    ) -> TopicMatchResult:
        """
        Provide topics by matching LLM-generated topics with existing DB topics.

        Algorithm:
        1. Generate 10 topics using LLM with web search
        2. Fetch DB topics for same business_domain + country
        3. If no DB topics: return all as unmatched GeneratedTopics
        4. Otherwise: match using embedding similarity (threshold 0.9)
        5. Return matched DB topics + unmatched GeneratedTopics

        Args:
            domain: Company domain
            business_domain: Business domain ORM object
            country: Country ORM object with eager-loaded languages

        Returns:
            TopicMatchResult with matched and unmatched topics
        """
        # Extract primary language from country
        primary_language = country.languages[0].name if country.languages else "English"

        # Step 1: Generate 10 topics using LLM (keep existing logic)
        generated_titles = await self._generate_topics_llm(
            domain, business_domain, primary_language
        )

        # Step 2: Fetch DB topics for business_domain + country
        db_topics = await self.topic_service.get_by_business_domain_and_country(
            business_domain.id, country.id
        )

        # Step 3: If no DB topics, return all as unmatched
        if not db_topics:
            logger.info(f"No DB topics found for {business_domain.name}/{country.iso_code}")
            return TopicMatchResult(
                matched_topics=[],
                unmatched_topics=[GeneratedTopic(title=t) for t in generated_titles]
            )

        # Step 4: Match using embedding similarity
        match_result = await self._match_topics_by_embedding(
            generated_titles, db_topics, similarity_threshold=0.9
        )

        logger.info(
            f"Topic matching: {len(match_result.matched_topics)} matched, "
            f"{len(match_result.unmatched_topics)} unmatched"
        )

        return match_result

    async def _generate_topics_llm(
        self,
        domain: str,
        business_domain: BusinessDomain,
        primary_language: str
    ) -> List[str]:
        """Generate 10 topics using LLM with web search (existing logic)."""
        # Route to appropriate prompt based on business domain name
        if business_domain.name == "e-comm":
            prompt = self._create_ecommerce_prompt(domain, primary_language)
        else:
            raise ValueError(f"Unsupported business domain: {business_domain.name}")

        response = await self.client.responses.create(
            model=self.model,
            tools=[{"type": "web_search"}],
            input=prompt
        )

        content = response.output_text
        if not content:
            raise ValueError("Empty response from OpenAI")

        json_content = self._extract_json(content)
        parsed_data = json.loads(json_content)

        if "top_topics" not in parsed_data:
            raise ValueError("Response missing 'top_topics' field")

        return parsed_data["top_topics"]

    async def _match_topics_by_embedding(
        self,
        generated_titles: List[str],
        db_topics: List[Topic],
        similarity_threshold: float = 0.9
    ) -> TopicMatchResult:
        """
        Match generated topic titles to DB topics using embedding similarity.

        Algorithm:
        1. Generate embeddings for all generated titles
        2. Generate embeddings for all DB topic titles
        3. Calculate cosine similarity matrix (n_generated × n_db)
        4. For each generated topic:
           - Find max similarity across all DB topics
           - If max_similarity >= 0.9: matched → add DB topic to matched list
           - Else: unmatched → add GeneratedTopic to unmatched list
        5. Return TopicMatchResult

        Args:
            generated_titles: List of LLM-generated topic titles
            db_topics: List of DB Topic ORM objects
            similarity_threshold: Minimum similarity for match (default: 0.9)

        Returns:
            TopicMatchResult with matched and unmatched topics
        """
        # Generate embeddings for generated titles
        generated_embeddings_list = self.embeddings_service.encode_keywords(generated_titles)
        generated_embeddings = np.array([e.embedding for e in generated_embeddings_list])

        # Generate embeddings for DB topic titles
        db_titles = [t.title for t in db_topics]
        db_embeddings_list = self.embeddings_service.encode_keywords(db_titles)
        db_embeddings = np.array([e.embedding for e in db_embeddings_list])

        # Calculate similarity matrix: (n_generated × n_db)
        similarity_matrix = cosine_similarity(generated_embeddings, db_embeddings)

        matched_topics = []
        unmatched_topics = []
        matched_db_indices = set()  # Track which DB topics have been matched

        # For each generated topic, find best match
        for gen_idx, gen_title in enumerate(generated_titles):
            # Find max similarity across all DB topics
            max_sim_idx = similarity_matrix[gen_idx].argmax()
            max_similarity = similarity_matrix[gen_idx, max_sim_idx]

            if max_similarity >= similarity_threshold:
                # Match found - use DB topic (avoid duplicates)
                if max_sim_idx not in matched_db_indices:
                    matched_topics.append(db_topics[max_sim_idx])
                    matched_db_indices.add(max_sim_idx)
                    logger.debug(
                        f"Matched '{gen_title}' → '{db_topics[max_sim_idx].title}' "
                        f"(similarity: {max_similarity:.3f})"
                    )
                else:
                    # DB topic already matched, treat as unmatched
                    unmatched_topics.append(GeneratedTopic(title=gen_title))
            else:
                # No match - use generated topic
                unmatched_topics.append(GeneratedTopic(title=gen_title))
                logger.debug(
                    f"No match for '{gen_title}' "
                    f"(max similarity: {max_similarity:.3f})"
                )

        return TopicMatchResult(
            matched_topics=matched_topics,
            unmatched_topics=unmatched_topics
        )

    def _extract_json(self, content: str) -> str:
        """Extract JSON from response, handling markdown code blocks."""
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    def _create_ecommerce_prompt(self, domain: str, primary_language: str) -> str:
        """Create prompt for e-commerce topics generation."""
        return f"""Analyze the e-commerce website at {domain} and extract sales categories.

TASK:
Identify the top 10 product sales categories (what they sell)

INSTRUCTIONS:
- Generate all topics in {primary_language} language
- Be specific (e.g., "Смартфони і телефони" not just "Electronics")
- Order by importance/popularity
- Focus on SALES CATEGORIES (what customers buy)

RESPONSE FORMAT:
Return ONLY valid JSON:
{{
  "top_topics": [
    "Category 1",
    "Category 2",
    "Category 3",
    "Category 4",
    "Category 5",
    "Category 6",
    "Category 7",
    "Category 8",
    "Category 9",
    "Category 10"
  ]
}}

Use web search to gather accurate information."""


def get_topics_provider(
    topic_service: TopicService = Depends(get_topic_service),
) -> TopicsProvider:
    """
    Dependency injection for TopicsProvider.

    Creates instance with:
    - API key and model from environment
    - TopicService (session-scoped via dependency injection)
    - EmbeddingsService (singleton)

    Args:
        topic_service: TopicService injected by FastAPI

    Returns:
        TopicsProvider instance for this request
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    model = os.getenv("TOPICS_GENERATION_MODEL", "gpt-4o-mini")
    embeddings_service = get_embeddings_service()  # Singleton (cached)

    return TopicsProvider(
        api_key=api_key,
        model=model,
        topic_service=topic_service,
        embeddings_service=embeddings_service
    )
