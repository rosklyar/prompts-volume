"""Pydantic API models for user deletion responses."""

from pydantic import BaseModel

from src.admin.user_deletion.protocol import DatabaseName


class DatabaseCleanupDetail(BaseModel):
    """Detail of cleanup for a single database."""

    database: DatabaseName
    deleted: dict[str, int]
    orphaned: dict[str, int]


class UserDeletionResponse(BaseModel):
    """Response model for user hard-delete endpoint."""

    user_id: str
    user_email: str
    total_records_deleted: int
    details: list[DatabaseCleanupDetail]
