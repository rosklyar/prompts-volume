"""Service for batch prompt upload with similarity matching."""

import uuid
from typing import Optional

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.evals_models import PriorityPromptQueue
from src.database.models import Prompt, PromptGroup, PromptGroupBinding
from src.embeddings.embeddings_service import EmbeddingsService
from src.prompt_groups.models.batch_models import (
    BatchAnalyzeResponse,
    BatchConfirmRequest,
    BatchConfirmResponse,
    BatchPromptAnalysis,
    SimilarPromptMatch,
)


class BatchUploadService:
    """Service for batch prompt upload with similarity matching.

    Handles:
    - Analyzing batch of prompts to find similar matches
    - Confirming selections (bind existing or create new via priority pipeline)
    """

    def __init__(
        self,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
        embeddings_service: EmbeddingsService,
        similarity_threshold: float,
        match_limit: int,
        max_prompts_per_batch: int,
    ):
        self._prompts_session = prompts_session
        self._evals_session = evals_session
        self._embeddings_service = embeddings_service
        self._similarity_threshold = similarity_threshold
        self._match_limit = match_limit
        self._max_prompts_per_batch = max_prompts_per_batch

    async def analyze_batch(
        self,
        prompt_texts: list[str],
    ) -> BatchAnalyzeResponse:
        """Analyze batch of prompts and find similar matches.

        Steps:
        1. Validate batch size
        2. Generate embeddings for all prompts in single batch
        3. For each embedding, query pgvector for top matches
        4. Return structured analysis results
        """
        if len(prompt_texts) > self._max_prompts_per_batch:
            raise ValueError(
                f"Batch size {len(prompt_texts)} exceeds maximum "
                f"{self._max_prompts_per_batch}"
            )

        # Generate embeddings for all prompts in batch
        text_embeddings = self._embeddings_service.encode_texts(
            prompt_texts,
            batch_size=32,
        )

        # Find similar matches for each prompt
        items: list[BatchPromptAnalysis] = []
        prompts_with_matches = 0

        for idx, text_with_embedding in enumerate(text_embeddings):
            matches = await self._find_similar_matches(
                text_with_embedding.embedding,
                limit=self._match_limit,
                min_similarity=self._similarity_threshold,
            )

            has_matches = len(matches) > 0
            if has_matches:
                prompts_with_matches += 1

            items.append(
                BatchPromptAnalysis(
                    index=idx,
                    input_text=text_with_embedding.text,
                    matches=matches,
                    has_matches=has_matches,
                )
            )

        return BatchAnalyzeResponse(
            items=items,
            total_prompts=len(prompt_texts),
            prompts_with_matches=prompts_with_matches,
            prompts_without_matches=len(prompt_texts) - prompts_with_matches,
        )

    async def confirm_batch(
        self,
        group: PromptGroup,
        request: BatchConfirmRequest,
    ) -> BatchConfirmResponse:
        """Process user selections and finalize batch.

        Steps:
        1. Separate into existing (to bind) vs new (to create)
        2. Bind existing prompts to group
        3. Create new prompts via priority pipeline pattern
        4. Bind newly created prompts to group
        5. Return summary
        """
        # Separate selections
        existing_prompt_ids: list[int] = []
        new_prompt_texts: list[str] = []
        new_prompt_indices: list[int] = []

        for selection in request.selections:
            if selection.use_existing and selection.selected_prompt_id is not None:
                existing_prompt_ids.append(selection.selected_prompt_id)
            else:
                new_prompt_texts.append(request.original_prompts[selection.index])
                new_prompt_indices.append(selection.index)

        # Bind existing prompts to group
        bound_existing = 0
        all_prompt_ids: list[int] = []

        if existing_prompt_ids:
            bound_count = await self._bind_prompts_to_group(group, existing_prompt_ids)
            bound_existing = bound_count
            all_prompt_ids.extend(existing_prompt_ids)

        # Create new prompts via priority pipeline pattern
        created_new = 0
        skipped_duplicates = 0

        if new_prompt_texts:
            result = await self._create_prompts_via_priority_pipeline(
                new_prompt_texts,
                group,
            )
            created_new = result["created_count"]
            skipped_duplicates = result["reused_count"]
            all_prompt_ids.extend(result["prompt_ids"])

        return BatchConfirmResponse(
            group_id=group.id,
            bound_existing=bound_existing,
            created_new=created_new,
            skipped_duplicates=skipped_duplicates,
            total_processed=len(request.selections),
            prompt_ids=all_prompt_ids,
        )

    async def _find_similar_matches(
        self,
        embedding: np.ndarray,
        limit: int,
        min_similarity: float,
    ) -> list[SimilarPromptMatch]:
        """Find similar prompts using pgvector cosine similarity."""
        # Convert similarity to max distance (cosine_distance = 1 - cosine_similarity)
        max_distance = 1.0 - min_similarity
        embedding_list = embedding.tolist()

        # Query using pgvector <=> operator (cosine distance)
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

    async def _bind_prompts_to_group(
        self,
        group: PromptGroup,
        prompt_ids: list[int],
    ) -> int:
        """Bind existing prompts to group. Returns count of newly bound prompts."""
        # Get existing bindings to avoid duplicates
        existing_stmt = select(PromptGroupBinding.prompt_id).where(
            PromptGroupBinding.group_id == group.id,
            PromptGroupBinding.prompt_id.in_(prompt_ids),
        )
        result = await self._prompts_session.execute(existing_stmt)
        existing_bound = {row[0] for row in result.all()}

        # Create new bindings
        bound_count = 0
        for prompt_id in prompt_ids:
            if prompt_id not in existing_bound:
                binding = PromptGroupBinding(
                    group_id=group.id,
                    prompt_id=prompt_id,
                )
                self._prompts_session.add(binding)
                bound_count += 1

        await self._prompts_session.flush()
        return bound_count

    async def _create_prompts_via_priority_pipeline(
        self,
        prompt_texts: list[str],
        group: PromptGroup,
        topic_id: Optional[int] = None,
    ) -> dict:
        """Create new prompts with deduplication and add to priority queue.

        Follows PriorityPromptService pattern:
        1. Generate embeddings
        2. Check for duplicates (99% similarity)
        3. Create new or reuse existing
        4. Add to priority queue
        5. Bind to group
        """
        # Generate embeddings
        text_embeddings = self._embeddings_service.encode_texts(
            prompt_texts,
            batch_size=32,
        )

        created_count = 0
        reused_count = 0
        prompt_ids: list[int] = []
        request_id = str(uuid.uuid4())

        for text_with_embedding in text_embeddings:
            prompt_text = text_with_embedding.text
            embedding = text_with_embedding.embedding

            # Search for duplicate with similarity >= 0.99
            existing_prompt, _ = await self._find_duplicate(
                embedding,
                similarity_threshold=0.99,
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

            # Add to priority queue (in evals_db)
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

            # Bind to group
            existing_binding = await self._prompts_session.execute(
                select(PromptGroupBinding).where(
                    PromptGroupBinding.group_id == group.id,
                    PromptGroupBinding.prompt_id == prompt_id,
                )
            )
            if not existing_binding.scalar_one_or_none():
                binding = PromptGroupBinding(
                    group_id=group.id,
                    prompt_id=prompt_id,
                )
                self._prompts_session.add(binding)

        await self._prompts_session.flush()
        await self._evals_session.flush()

        return {
            "created_count": created_count,
            "reused_count": reused_count,
            "prompt_ids": prompt_ids,
            "request_id": request_id,
        }

    async def _find_duplicate(
        self,
        embedding: np.ndarray,
        similarity_threshold: float = 0.99,
    ) -> tuple[Optional[Prompt], Optional[float]]:
        """Search for existing prompt with similarity >= threshold."""
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
                return closest_prompt, cosine_similarity

        return None, None
