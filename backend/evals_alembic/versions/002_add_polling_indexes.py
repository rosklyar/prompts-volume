"""Add composite indexes for poll_for_prompt scalability

Revision ID: 002
Revises: 001
Create Date: 2024-12-29

Adds partial composite indexes to optimize the locked_subquery in poll_for_prompt:
- idx_pe_poll_in_progress: For IN_PROGRESS claim detection
- idx_pe_poll_completed: For COMPLETED re-evaluation check
- idx_pe_claimed_at: For timeout filtering on claimed_at

These indexes support the query pattern:
    SELECT prompt_id FROM prompt_evaluations
    WHERE assistant_plan_id = ?
      AND ((status = 'in_progress' AND claimed_at > ?)
        OR (status = 'completed' AND completed_at > ?))

Expected improvement: 10-100x faster poll queries at scale (1M+ evaluations).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite indexes for poll_for_prompt optimization."""
    # Partial index for IN_PROGRESS claim detection
    # Covers: WHERE assistant_plan_id = ? AND status = 'in_progress' AND claimed_at > ?
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pe_poll_in_progress
        ON prompt_evaluations(assistant_plan_id, prompt_id, claimed_at DESC)
        WHERE status = 'in_progress'
    """)

    # Partial index for COMPLETED re-evaluation check
    # Covers: WHERE assistant_plan_id = ? AND status = 'completed' AND completed_at > ?
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pe_poll_completed
        ON prompt_evaluations(assistant_plan_id, prompt_id, completed_at DESC)
        WHERE status = 'completed'
    """)

    # Standalone index on claimed_at for timeout filtering
    # Useful for: WHERE status = 'in_progress' AND claimed_at > ?
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pe_claimed_at
        ON prompt_evaluations(claimed_at DESC)
        WHERE status = 'in_progress'
    """)


def downgrade() -> None:
    """Remove composite indexes."""
    op.drop_index("idx_pe_poll_in_progress", table_name="prompt_evaluations")
    op.drop_index("idx_pe_poll_completed", table_name="prompt_evaluations")
    op.drop_index("idx_pe_claimed_at", table_name="prompt_evaluations")
