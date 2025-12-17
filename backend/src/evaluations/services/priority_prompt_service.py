"""Service for managing priority prompt queue."""

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Prompt, PriorityPromptQueue
from src.embeddings.embeddings_service import EmbeddingsService


class PriorityPromptService:
    """Service for managing priority prompt queue."""

    def __init__(
        self,
        session: AsyncSession,
        embeddings_service: EmbeddingsService,
        max_prompts_per_request: int,
    ):
        self.session = session
        self.embeddings_service = embeddings_service
        self.max_prompts_per_request = max_prompts_per_request

    async def add_priority_prompts(
        self,
        prompt_texts: List[str],
        topic_id: Optional[int] = None,
    ) -> dict:
        """
        Add prompts to DB and priority queue.

        Steps:
        1. Validate batch size
        2. Generate embeddings for all prompts (batch)
        3. For each prompt:
           - Search for duplicates (similarity >= 0.99)
           - If found: reuse existing prompt_id
           - If not: create new Prompt record
        4. Add all prompt_ids to PriorityPromptQueue
        5. Return results with duplicate indicators
        """
        # Step 1: Validate batch size
        if len(prompt_texts) > self.max_prompts_per_request:
            raise ValueError(
                f"Batch size {len(prompt_texts)} exceeds maximum "
                f"{self.max_prompts_per_request}"
            )

        # Step 2: Generate embeddings for all prompts (batch)
        embeddings = self.embeddings_service.encode_texts(
            prompt_texts,
            batch_size=32,
        )

        # Step 3: Process each prompt (check duplicates, create if needed)
        results = []
        created_count = 0
        reused_count = 0

        for text_with_embedding in embeddings:
            prompt_text = text_with_embedding.text
            embedding = text_with_embedding.embedding

            # Search for duplicate with similarity >= 0.99
            existing_prompt, similarity = await self._find_duplicate(
                embedding, similarity_threshold=0.99
            )

            if existing_prompt:
                # Reuse existing prompt
                prompt_id = existing_prompt.id
                was_duplicate = True
                reused_count += 1
            else:
                # Create new prompt
                new_prompt = Prompt(
                    prompt_text=prompt_text,
                    embedding=embedding.tolist(),
                    topic_id=topic_id,
                )
                self.session.add(new_prompt)
                await self.session.flush()
                prompt_id = new_prompt.id
                was_duplicate = False
                similarity = None
                created_count += 1

            results.append({
                "prompt_id": prompt_id,
                "prompt_text": prompt_text,
                "topic_id": topic_id,
                "was_duplicate": was_duplicate,
                "similarity_score": similarity,
            })

        # Step 4: Add all prompt_ids to priority queue
        request_id = str(uuid.uuid4())
        for result in results:
            # Check if already in queue (unique constraint)
            existing = await self.session.execute(
                select(PriorityPromptQueue).where(
                    PriorityPromptQueue.prompt_id == result["prompt_id"]
                )
            )
            if not existing.scalar_one_or_none():
                queue_entry = PriorityPromptQueue(
                    prompt_id=result["prompt_id"],
                    request_id=request_id,
                )
                self.session.add(queue_entry)

        await self.session.flush()

        return {
            "created_count": created_count,
            "reused_count": reused_count,
            "total_count": len(results),
            "prompts": results,
            "request_id": request_id,
        }

    async def _find_duplicate(
        self,
        embedding: list,
        similarity_threshold: float = 0.99,
    ) -> tuple[Optional[Prompt], Optional[float]]:
        """
        Search for existing prompt with similarity >= threshold.

        Uses pgvector cosine distance operator (<=>).
        Returns (Prompt, similarity) if found, (None, None) otherwise.
        """
        # Cosine similarity = 1 - cosine_distance
        # So we want: 1 - distance >= threshold
        # => distance <= 1 - threshold
        max_distance = 1.0 - similarity_threshold

        query = (
            select(Prompt)
            .order_by(Prompt.embedding.cosine_distance(embedding))
            .limit(1)
        )

        result = await self.session.execute(query)
        closest_prompt = result.scalar_one_or_none()

        if closest_prompt:
            # Calculate actual similarity using numpy
            # Convert embedding to numpy array if needed
            import numpy as np
            prompt_emb = np.array(closest_prompt.embedding)
            query_emb = np.array(embedding)

            # Cosine distance = 1 - cosine similarity
            # Cosine similarity = dot product / (norm1 * norm2)
            cosine_similarity = np.dot(prompt_emb, query_emb) / (
                np.linalg.norm(prompt_emb) * np.linalg.norm(query_emb)
            )
            distance = 1.0 - cosine_similarity
            similarity = cosine_similarity

            if similarity >= similarity_threshold:
                return closest_prompt, similarity

        return None, None


def get_priority_prompt_service(
    session: AsyncSession,
    embeddings_service: EmbeddingsService,
    max_prompts: int,
) -> PriorityPromptService:
    """Dependency injection for PriorityPromptService."""
    return PriorityPromptService(session, embeddings_service, max_prompts)
