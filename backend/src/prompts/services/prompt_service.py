"""Prompt service for database operations."""

from dataclasses import dataclass
from typing import List

from fastapi import Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import Prompt, get_async_session
from src.embeddings.embeddings_service import EmbeddingsService, get_embeddings_service


@dataclass
class SimilarPromptResult:
    """Internal result for similar prompt query."""

    id: int
    prompt_text: str
    similarity: float


class PromptService:
    """Service for managing prompts in the database."""

    def __init__(
        self,
        session: AsyncSession,
        embeddings_service: EmbeddingsService,
    ):
        """
        Initialize PromptService with a database session and embeddings service.

        Args:
            session: AsyncSession for database operations
            embeddings_service: Service for generating embeddings
        """
        self.session = session
        self.embeddings_service = embeddings_service

    async def get_by_ids(self, prompt_ids: list[int]) -> dict[int, str]:
        """Get prompt texts by IDs.

        Args:
            prompt_ids: List of prompt IDs

        Returns:
            Dict mapping prompt_id to prompt_text
        """
        result = await self.session.execute(
            select(Prompt).where(Prompt.id.in_(prompt_ids))
        )
        return {p.id: p.prompt_text for p in result.scalars().all()}

    async def get_by_topic_ids(self, topic_ids: List[int]) -> List[Prompt]:
        """
        Get all prompts for the given topic IDs.

        Args:
            topic_ids: List of topic IDs

        Returns:
            List of Prompt objects for the specified topics
        """
        result = await self.session.execute(
            select(Prompt)
            .where(Prompt.topic_id.in_(topic_ids))
            .order_by(Prompt.topic_id, Prompt.id)
        )
        return list(result.scalars().all())

    async def add_prompt(self, prompt_text: str, topic_id: int) -> Prompt:
        """
        Add a new prompt with automatically generated embedding.

        Args:
            prompt_text: The text of the prompt
            topic_id: The ID of the topic this prompt belongs to

        Returns:
            Created Prompt object with embedding
        """
        # Generate embedding for the prompt text
        text_embeddings = self.embeddings_service.encode_texts([prompt_text])
        embedding = text_embeddings[0].embedding

        # Create and save prompt
        prompt = Prompt(
            prompt_text=prompt_text,
            embedding=embedding.tolist(),
            topic_id=topic_id,
        )
        self.session.add(prompt)
        await self.session.flush()
        await self.session.refresh(prompt)
        return prompt

    async def find_similar(
        self,
        query_text: str,
        limit: int,
        min_similarity: float,
    ) -> List[SimilarPromptResult]:
        """
        Find similar prompts using pgvector cosine similarity.

        Uses the HNSW index on the embedding column for efficient
        approximate nearest neighbor search.

        Args:
            query_text: The text to find similar prompts for
            limit: Maximum number of results to return
            min_similarity: Minimum cosine similarity threshold (0-1)

        Returns:
            List of SimilarPromptResult sorted by similarity (highest first)
        """
        # Generate embedding for query text
        text_embeddings = self.embeddings_service.encode_texts([query_text])
        query_embedding = text_embeddings[0].embedding.tolist()

        # Convert similarity to max distance (cosine_distance = 1 - cosine_similarity)
        max_distance = 1.0 - min_similarity

        # Query using pgvector <=> operator (cosine distance)
        # Uses HNSW index for efficient ANN search
        result = await self.session.execute(
            text("""
                SELECT id, prompt_text, 1 - (embedding <=> :query_embedding) AS similarity
                FROM prompts
                WHERE (embedding <=> :query_embedding) <= :max_distance
                ORDER BY embedding <=> :query_embedding
                LIMIT :limit
            """),
            {
                "query_embedding": str(query_embedding),
                "max_distance": max_distance,
                "limit": limit,
            },
        )

        return [
            SimilarPromptResult(id=row.id, prompt_text=row.prompt_text, similarity=row.similarity)
            for row in result.fetchall()
        ]


def get_prompt_service(
    session: AsyncSession = Depends(get_async_session),
    embeddings_service: EmbeddingsService = Depends(get_embeddings_service),
) -> PromptService:
    """
    Dependency injection function for PromptService.

    Creates a new PromptService instance per request with the request-scoped session.

    Args:
        session: AsyncSession injected by FastAPI (new session per request)
        embeddings_service: Singleton EmbeddingsService instance

    Returns:
        PromptService instance for this request
    """
    return PromptService(session, embeddings_service)
