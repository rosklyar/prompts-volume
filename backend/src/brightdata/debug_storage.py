"""Thread-safe debug storage for webhook payloads."""

from collections import deque
from threading import Lock
from typing import Any


class WebhookDebugStorage:
    """Thread-safe bounded storage for webhook debug payloads.

    Uses a deque with maxlen for automatic eviction of old entries.
    All operations are protected by a lock for thread safety.
    """

    def __init__(self, max_size: int = 10) -> None:
        self._payloads: deque[dict[str, Any]] = deque(maxlen=max_size)
        self._lock = Lock()

    def add(self, batch_id: str, assistant_key: str, payload: Any) -> None:
        """Add a new webhook payload to storage."""
        with self._lock:
            self._payloads.append({
                "batch_id": batch_id,
                "assistant_key": assistant_key,
                "payload": payload,
            })

    def get_all(self) -> list[dict[str, Any]]:
        """Get all stored payloads."""
        with self._lock:
            return list(self._payloads)

    def count(self) -> int:
        """Get number of stored payloads."""
        with self._lock:
            return len(self._payloads)


# Singleton instance
webhook_debug_storage = WebhookDebugStorage(max_size=10)
