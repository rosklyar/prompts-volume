"""Replace priority_prompt_queue with execution_queue

Revision ID: 002
Revises: 001
Create Date: 2025-01-07

Replaces the old priority queue with the new demand-driven execution queue.
Key changes:
- Drop priority_prompt_queue table
- Create execution_queue table with:
  - Status tracking (pending, in_progress, completed, failed, cancelled)
  - User tracking (who requested the execution)
  - Batch grouping (request_batch_id)
  - Evaluation reference
  - Partial unique constraint on prompt_id for active items
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace priority_prompt_queue with execution_queue."""
    # Drop the old priority_prompt_queue table
    op.drop_index("ix_priority_prompt_queue_request_id", table_name="priority_prompt_queue")
    op.drop_index("ix_priority_prompt_queue_created_at", table_name="priority_prompt_queue")
    op.drop_index("ix_priority_prompt_queue_prompt_id", table_name="priority_prompt_queue")
    op.drop_table("priority_prompt_queue")

    # Create executionqueuestatus enum
    op.execute("CREATE TYPE executionqueuestatus AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'cancelled')")
    executionqueuestatus_enum = postgresql.ENUM(
        "pending", "in_progress", "completed", "failed", "cancelled",
        name="executionqueuestatus",
        create_type=False
    )

    # Create execution_queue table
    op.create_table(
        "execution_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt_id", sa.Integer(), nullable=False),  # No FK - prompts in prompts_db
        sa.Column("requested_by", sa.String(36), nullable=False),  # User ID or 'system'
        sa.Column("request_batch_id", sa.String(100), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("status", executionqueuestatus_enum, nullable=False, server_default="pending"),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluation_id", sa.Integer(), sa.ForeignKey("prompt_evaluations.id", ondelete="SET NULL"), nullable=True),
    )

    # Create indexes
    op.create_index("ix_execution_queue_prompt_id", "execution_queue", ["prompt_id"])
    op.create_index("ix_execution_queue_requested_by", "execution_queue", ["requested_by"])
    op.create_index("ix_execution_queue_request_batch_id", "execution_queue", ["request_batch_id"])
    op.create_index("ix_execution_queue_requested_at", "execution_queue", ["requested_at"])
    op.create_index("ix_execution_queue_status", "execution_queue", ["status"])
    op.create_index("ix_execution_queue_evaluation_id", "execution_queue", ["evaluation_id"])

    # Create partial unique constraint for active items (GLOBAL uniqueness)
    # Prompt can only be in queue once when status is 'pending' or 'in_progress'
    op.execute("""
        CREATE UNIQUE INDEX uq_execution_queue_prompt_active
        ON execution_queue(prompt_id)
        WHERE status IN ('pending', 'in_progress')
    """)

    # Create partial index for efficient FIFO polling
    op.execute("""
        CREATE INDEX idx_eq_poll_pending
        ON execution_queue(requested_at ASC)
        WHERE status = 'pending'
    """)


def downgrade() -> None:
    """Restore priority_prompt_queue (without data)."""
    # Drop execution_queue
    op.drop_index("idx_eq_poll_pending", table_name="execution_queue")
    op.drop_index("uq_execution_queue_prompt_active", table_name="execution_queue")
    op.drop_index("ix_execution_queue_evaluation_id", table_name="execution_queue")
    op.drop_index("ix_execution_queue_status", table_name="execution_queue")
    op.drop_index("ix_execution_queue_requested_at", table_name="execution_queue")
    op.drop_index("ix_execution_queue_request_batch_id", table_name="execution_queue")
    op.drop_index("ix_execution_queue_requested_by", table_name="execution_queue")
    op.drop_index("ix_execution_queue_prompt_id", table_name="execution_queue")
    op.drop_table("execution_queue")
    op.execute("DROP TYPE IF EXISTS executionqueuestatus")

    # Recreate priority_prompt_queue
    op.create_table(
        "priority_prompt_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("request_id", sa.String(100), nullable=False),
    )
    op.create_index("ix_priority_prompt_queue_prompt_id", "priority_prompt_queue", ["prompt_id"])
    op.create_index("ix_priority_prompt_queue_created_at", "priority_prompt_queue", ["created_at"])
    op.create_index("ix_priority_prompt_queue_request_id", "priority_prompt_queue", ["request_id"])
