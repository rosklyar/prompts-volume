"""Shared service for batch prompt operations."""

import uuid
from typing import Annotated

import numpy as np
from fastapi import Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database import get_async_session
from src.database.evals_models import PriorityPromptQueue
from src.database.evals_session import get_evals_session
from src.database.models import Prompt
from src.embeddings.embeddings_service import EmbeddingsService, get_embeddings_service
from src.prompts.batch.models import (
    BatchAnalyzeResponse,
    BatchCreateResponse,
    BatchPromptAnalysis,
    SimilarPromptMatch,
)


class BatchPromptsService:
    """Shared service for batch prompt operations.

    Used by both regular users (adding to groups) and admins (uploading to topics).
    """

    def __init__(
        self,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
        embeddings_service: EmbeddingsService,
        similarity_threshold: float,
        match_limit: int,
        duplicate_threshold: float,
        max_prompts: int,
    ):
        self._prompts_session = prompts_session
        self._evals_session = evals_session
        self._embeddings_service = embeddings_service
        self._similarity_threshold = similarity_threshold
        self._match_limit = match_limit
        self._duplicate_threshold = duplicate_threshold
        self._max_prompts = max_prompts

    async def analyze_batch(self, prompts: list[str]) -> BatchAnalyzeResponse:
        """Analyze batch of prompts and find similar matches.

        For each prompt:
        - Returns top N matches if similarity >= similarity_threshold
        - Marks as duplicate if best match >= duplicate_threshold
        """
        if len(prompts) > self._max_prompts:
            raise ValueError(
                f"Batch size {len(prompts)} exceeds maximum {self._max_prompts}"
            )

        # Generate embeddings for all prompts in batch
        text_embeddings = self._embeddings_service.encode_texts(
            prompts,
            batch_size=32,
        )

        items: list[BatchPromptAnalysis] = []
        duplicates_count = 0
        with_matches_count = 0

        for idx, text_with_embedding in enumerate(text_embeddings):
            matches = await self._find_similar_matches(
                text_with_embedding.embedding,
                limit=self._match_limit,
                min_similarity=self._similarity_threshold,
            )

            has_matches = len(matches) > 0
            if has_matches:
                with_matches_count += 1

            # Check if best match is a duplicate
            is_duplicate = False
            if matches and matches[0].similarity >= self._duplicate_threshold:
                is_duplicate = True
                duplicates_count += 1

            items.append(
                BatchPromptAnalysis(
                    index=idx,
                    input_text=text_with_embedding.text,
                    matches=matches,
                    has_matches=has_matches,
                    is_duplicate=is_duplicate,
                )
            )

        return BatchAnalyzeResponse(
            items=items,
            total_prompts=len(prompts),
            duplicates_count=duplicates_count,
            with_matches_count=with_matches_count,
        )

    async def create_prompts(
        self,
        prompts: list[str],
        selected_indices: list[int],
        topic_id: int | None = None,
    ) -> BatchCreateResponse:
        """Create new prompts via priority pipeline.

        For each selected prompt:
        1. Generate embedding
        2. Check for duplicate (>= duplicate_threshold similarity)
        3. If duplicate: reuse existing prompt
        4. If new: create prompt with optional topic_id
        5. Add to priority queue

        Args:
            prompts: All original prompt texts
            selected_indices: Indices of prompts to create
            topic_id: Optional topic ID to assign to new prompts

        Returns:
            BatchCreateResponse with created/reused counts and prompt IDs
        """
        # Filter to selected prompts only
        selected_texts = [
            prompts[i] for i in selected_indices if i < len(prompts)
        ]

        if not selected_texts:
            raise ValueError("No valid prompts selected for creation")

        # Generate embeddings
        text_embeddings = self._embeddings_service.encode_texts(
            selected_texts,
            batch_size=32,
        )

        created_count = 0
        reused_count = 0
        prompt_ids: list[int] = []
        request_id = str(uuid.uuid4())

        for text_with_embedding in text_embeddings:
            prompt_text = text_with_embedding.text
            embedding = text_with_embedding.embedding

            # Check for duplicate
            existing_prompt = await self._find_duplicate(
                embedding,
                similarity_threshold=self._duplicate_threshold,
            )

            if existing_prompt:
                # Reuse existing prompt
                prompt_id = existing_prompt.id
                reused_count += 1
            else:
                # Create new prompt
                new_prompt = Prompt(
                    prompt_text=prompt_text,
                    embedding=embedding.tolist(),
                    topic_id=topic_id,
                )
                self._prompts_session.add(new_prompt)
                await self._prompts_session.flush()
                prompt_id = new_prompt.id
                created_count += 1

            prompt_ids.append(prompt_id)

            # Add to priority queue (in evals_db) if not already there
            existing_queue = await self._evals_session.execute(
                select(PriorityPromptQueue).where(
                    PriorityPromptQueue.prompt_id == prompt_id
                )
            )
            if not existing_queue.scalar_one_or_none():
                queue_entry = PriorityPromptQueue(
                    prompt_id=prompt_id,
                    request_id=request_id,
                )
                self._evals_session.add(queue_entry)

        await self._prompts_session.flush()
        await self._evals_session.flush()

        return BatchCreateResponse(
            created_count=created_count,
            reused_count=reused_count,
            prompt_ids=prompt_ids,
            request_id=request_id,
        )

    async def _find_similar_matches(
        self,
        embedding: np.ndarray,
        limit: int,
        min_similarity: float,
    ) -> list[SimilarPromptMatch]:
        """Find similar prompts using pgvector cosine similarity."""
        max_distance = 1.0 - min_similarity
        embedding_list = embedding.tolist()

        result = await self._prompts_session.execute(
            text("""
                SELECT id, prompt_text, 1 - (embedding <=> :query_embedding) AS similarity
                FROM prompts
                WHERE (embedding <=> :query_embedding) <= :max_distance
                ORDER BY embedding <=> :query_embedding
                LIMIT :limit
            """),
            {
                "query_embedding": str(embedding_list),
                "max_distance": max_distance,
                "limit": limit,
            },
        )

        return [
            SimilarPromptMatch(
                prompt_id=row.id,
                prompt_text=row.prompt_text,
                similarity=row.similarity,
            )
            for row in result.fetchall()
        ]

    async def _find_duplicate(
        self,
        embedding: np.ndarray,
        similarity_threshold: float,
    ) -> Prompt | None:
        """Find existing prompt with similarity >= threshold."""
        embedding_list = embedding.tolist()

        query = (
            select(Prompt)
            .order_by(Prompt.embedding.cosine_distance(embedding_list))
            .limit(1)
        )

        result = await self._prompts_session.execute(query)
        closest_prompt = result.scalar_one_or_none()

        if closest_prompt:
            # Calculate actual similarity
            prompt_emb = np.array(closest_prompt.embedding)
            query_emb = np.array(embedding_list)

            cosine_similarity = np.dot(prompt_emb, query_emb) / (
                np.linalg.norm(prompt_emb) * np.linalg.norm(query_emb)
            )

            if cosine_similarity >= similarity_threshold:
                return closest_prompt

        return None


def get_batch_prompts_service(
    prompts_session: Annotated[AsyncSession, Depends(get_async_session)],
    evals_session: Annotated[AsyncSession, Depends(get_evals_session)],
) -> BatchPromptsService:
    """Dependency injection for BatchPromptsService."""
    return BatchPromptsService(
        prompts_session=prompts_session,
        evals_session=evals_session,
        embeddings_service=get_embeddings_service(),
        similarity_threshold=settings.batch_upload_similarity_threshold,
        match_limit=settings.batch_upload_match_limit,
        duplicate_threshold=settings.batch_upload_duplicate_threshold,
        max_prompts=settings.batch_upload_max_prompts,
    )
