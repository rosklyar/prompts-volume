"""Prompt service for database operations."""

from typing import List

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import Prompt, get_async_session
from src.embeddings.embeddings_service import EmbeddingsService, get_embeddings_service


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
