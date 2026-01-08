"""Protocols for execution queue operations.

Defines abstract interfaces for queue operations following
Interface Segregation Principle:
- QueueReader: Read-only operations
- QueueWriter: Write operations
- QueuePoller: Bot-specific polling operations
"""

from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from src.database.evals_models import ExecutionQueueStatus


@dataclass
class QueueEntry:
    """Domain model for a queue entry."""

    id: int
    prompt_id: int
    requested_by: str
    request_batch_id: str
    requested_at: datetime
    status: ExecutionQueueStatus
    claimed_at: datetime | None = None
    completed_at: datetime | None = None
    evaluation_id: int | None = None


@dataclass
class AddToQueueResult:
    """Result of adding prompts to queue."""

    queued_count: int
    skipped_count: int  # Already in queue
    total_queue_size: int
    queued_entries: list[QueueEntry]


class QueueReader(Protocol):
    """Protocol for reading from execution queue."""

    @abstractmethod
    async def get_pending_count(self) -> int:
        """Get total number of pending items in queue."""
        ...

    @abstractmethod
    async def get_user_pending_items(self, user_id: str) -> list[QueueEntry]:
        """Get all pending/in_progress items for a user."""
        ...

    @abstractmethod
    async def is_prompt_in_queue(self, prompt_id: int) -> bool:
        """Check if prompt is already in queue (pending or in_progress)."""
        ...


class QueueWriter(Protocol):
    """Protocol for writing to execution queue."""

    @abstractmethod
    async def add_to_queue(
        self,
        prompt_ids: list[int],
        user_id: str,
        batch_id: str,
    ) -> AddToQueueResult:
        """
        Add prompts to execution queue.

        Skips prompts that are already in queue (global uniqueness).
        Returns (queued_count, skipped_count, total_queue_size).
        """
        ...

    @abstractmethod
    async def cancel_pending(
        self,
        prompt_ids: list[int],
        user_id: str,
    ) -> int:
        """
        Cancel pending items for user.

        Only cancels PENDING items (not IN_PROGRESS).
        Returns count cancelled.
        """
        ...


class QueuePoller(Protocol):
    """Protocol for bot polling operations."""

    @abstractmethod
    async def poll_next(
        self,
        assistant_plan_id: int,
    ) -> tuple[QueueEntry, int] | None:
        """
        Atomically claim next item from queue (FIFO order).

        Uses SELECT FOR UPDATE SKIP LOCKED for concurrency.
        Also handles timeout cleanup (IN_PROGRESS > timeout reset to PENDING).

        Returns (queue_entry, prompt_id) or None if queue empty.
        """
        ...

    @abstractmethod
    async def mark_completed(
        self,
        queue_entry_id: int,
        evaluation_id: int,
    ) -> None:
        """Mark queue entry as completed with evaluation reference."""
        ...

    @abstractmethod
    async def mark_failed(
        self,
        queue_entry_id: int,
        reason: str,
    ) -> None:
        """Mark queue entry as failed."""
        ...
