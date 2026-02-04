"""Admin user deletion module."""

from src.admin.user_deletion.exceptions import (
    CannotDeleteSelfError,
    CannotDeleteSuperuserError,
    UserDeletionError,
    UserNotFoundError,
)
from src.admin.user_deletion.models import DatabaseCleanupDetail, UserDeletionResponse
from src.admin.user_deletion.orchestrator import DeletionSummary, UserDeletionOrchestrator
from src.admin.user_deletion.protocol import CleanupResult, UserDataCleaner
from src.admin.user_deletion.service import (
    UserDeletionService,
    UserDeletionServiceDep,
    get_user_deletion_service,
)

__all__ = [
    # Exceptions
    "CannotDeleteSelfError",
    "CannotDeleteSuperuserError",
    "UserDeletionError",
    "UserNotFoundError",
    # Models
    "DatabaseCleanupDetail",
    "UserDeletionResponse",
    # Orchestrator
    "DeletionSummary",
    "UserDeletionOrchestrator",
    # Protocol
    "CleanupResult",
    "UserDataCleaner",
    # Service
    "UserDeletionService",
    "UserDeletionServiceDep",
    "get_user_deletion_service",
]
