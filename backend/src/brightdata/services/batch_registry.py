"""In-memory batch tracking registry."""

import logging
from datetime import datetime, timedelta, timezone
from threading import Lock

from src.brightdata.models.domain import BatchInfo, BatchStatus, ParsedResult
from src.config.settings import settings

logger = logging.getLogger(__name__)


class InMemoryBatchRegistry:
    """In-memory registry for tracking Bright Data batches and results.

    Thread-safe implementation using Lock.
    Auto-expires batches older than TTL.
    """

    def __init__(self, ttl_hours: int = 24):
        """Initialize registry.

        Args:
            ttl_hours: Hours before batch expires and is removed
        """
        self._batches: dict[str, BatchInfo] = {}
        self._lock = Lock()
        self._ttl = timedelta(hours=ttl_hours)

    def _cleanup_expired(self) -> None:
        """Remove expired batches (called under lock)."""
        now = datetime.now(timezone.utc)
        expired = [
            batch_id
            for batch_id, info in self._batches.items()
            if now - info.created_at > self._ttl
        ]
        for batch_id in expired:
            logger.info(f"Removing expired batch {batch_id}")
            del self._batches[batch_id]

    def register_batch(
        self,
        batch_id: str,
        prompt_id_to_text: dict[int, str],
        user_id: str,
    ) -> None:
        """Register a new batch with prompt mappings."""
        with self._lock:
            self._cleanup_expired()

            # Build reverse lookup
            text_to_prompt_id = {text: pid for pid, text in prompt_id_to_text.items()}

            self._batches[batch_id] = BatchInfo(
                batch_id=batch_id,
                user_id=user_id,
                prompt_id_to_text=prompt_id_to_text,
                text_to_prompt_id=text_to_prompt_id,
                created_at=datetime.now(timezone.utc),
            )
            logger.info(
                f"Registered batch {batch_id} with {len(prompt_id_to_text)} prompts"
            )

    def get_batch(self, batch_id: str) -> BatchInfo | None:
        """Get batch info by ID. Returns None if not found or expired."""
        with self._lock:
            self._cleanup_expired()
            return self._batches.get(batch_id)

    def get_prompt_id_by_text(
        self,
        batch_id: str,
        prompt_text: str,
    ) -> int | None:
        """Reverse lookup: find prompt_id from prompt_text within a batch."""
        with self._lock:
            batch = self._batches.get(batch_id)
            if not batch:
                return None
            return batch.text_to_prompt_id.get(prompt_text)

    def add_result(self, batch_id: str, result: ParsedResult) -> None:
        """Add a parsed result to the batch."""
        with self._lock:
            batch = self._batches.get(batch_id)
            if batch:
                batch.results.append(result)

    def add_error(self, batch_id: str, error: str) -> None:
        """Add an error message to the batch."""
        with self._lock:
            batch = self._batches.get(batch_id)
            if batch:
                batch.errors.append(error)

    def complete_batch(self, batch_id: str, status: BatchStatus) -> None:
        """Mark batch as completed with given status."""
        with self._lock:
            batch = self._batches.get(batch_id)
            if batch:
                batch.status = status
                logger.info(f"Batch {batch_id} completed with status {status}")

    def get_all_batches(self) -> list[BatchInfo]:
        """Get all non-expired batches."""
        with self._lock:
            self._cleanup_expired()
            return list(self._batches.values())


# Global singleton with thread-safe initialization
_batch_registry: InMemoryBatchRegistry | None = None
_registry_lock = Lock()


def get_batch_registry() -> InMemoryBatchRegistry:
    """Get global batch registry singleton (thread-safe)."""
    global _batch_registry
    if _batch_registry is None:
        with _registry_lock:
            if _batch_registry is None:  # Double-check pattern
                _batch_registry = InMemoryBatchRegistry(
                    ttl_hours=settings.brightdata_batch_ttl_hours
                )
    return _batch_registry
