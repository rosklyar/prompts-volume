"""Shared service for batch prompt operations."""

import uuid
from typing import Annotated

import numpy as np
from fastapi import Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database import get_async_session
from src.database.evals_models import ExecutionQueue, ExecutionQueueStatus
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
        """Create new prompts (already filtered by analyze step).

        All selected prompts are created as new entries - no duplicate detection.
        The analyze step shows duplicates and users select only new prompts.

        Args:
            prompts: All original prompt texts
            selected_indices: Indices of prompts to create (non-duplicates)
            topic_id: Optional topic ID to assign to new prompts

        Returns:
            BatchCreateResponse with created count and prompt IDs
        """
        selected_texts = [
            prompts[i] for i in selected_indices if i < len(prompts)
        ]

        if not selected_texts:
            raise ValueError("No valid prompts selected for creation")

        text_embeddings = self._embeddings_service.encode_texts(
            selected_texts,
            batch_size=32,
        )

        prompt_ids: list[int] = []
        request_id = str(uuid.uuid4())

        for text_with_embedding in text_embeddings:
            new_prompt = Prompt(
                prompt_text=text_with_embedding.text,
                embedding=text_with_embedding.embedding.tolist(),
                topic_id=topic_id,
            )
            self._prompts_session.add(new_prompt)
            await self._prompts_session.flush()
            prompt_ids.append(new_prompt.id)

            # Add to execution queue for immediate execution
            queue_entry = ExecutionQueue(
                prompt_id=new_prompt.id,
                requested_by="system",  # Admin-added prompts
                request_batch_id=request_id,
                status=ExecutionQueueStatus.PENDING,
            )
            self._evals_session.add(queue_entry)

        await self._evals_session.flush()

        return BatchCreateResponse(
            created_count=len(prompt_ids),
            reused_count=0,
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
