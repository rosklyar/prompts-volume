"""Approval policies for determining initial prompt status.

Strategy pattern allows swapping approval logic without changing services.
"""

from typing import Protocol

from src.database import PromptApprovalStatus


class ApprovalPolicy(Protocol):
    """Policy for determining initial approval status of a prompt."""

    def determine_initial_status(
        self,
        *,
        has_topic: bool,
        user_is_admin: bool,
    ) -> PromptApprovalStatus:
        """Determine what status a new prompt should have.

        Args:
            has_topic: Whether the prompt's group has an assigned topic
            user_is_admin: Whether the creating user is a superuser

        Returns:
            Initial approval status for the prompt
        """
        ...


class DefaultApprovalPolicy:
    """Default approval policy per requirements.

    - Admin-created prompts: APPROVED
    - User prompts (with or without topic): PENDING
    """

    def determine_initial_status(
        self,
        *,
        has_topic: bool,
        user_is_admin: bool,
    ) -> PromptApprovalStatus:
        if user_is_admin:
            return PromptApprovalStatus.APPROVED
        return PromptApprovalStatus.PENDING


def get_approval_policy() -> ApprovalPolicy:
    """Get the default approval policy."""
    return DefaultApprovalPolicy()
