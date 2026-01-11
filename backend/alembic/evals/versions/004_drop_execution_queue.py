"""Drop execution_queue table.

Revision ID: 004
Revises: 003
Create Date: 2025-01-11

The old bot-polling execution system has been replaced by
Bright Data webhook-based system. This migration removes
the now-unused execution_queue table.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop all indexes first
    op.drop_index("idx_eq_poll_pending", table_name="execution_queue", if_exists=True)
    op.drop_index("uq_execution_queue_prompt_active", table_name="execution_queue", if_exists=True)
    op.drop_index("ix_execution_queue_evaluation_id", table_name="execution_queue", if_exists=True)
    op.drop_index("ix_execution_queue_status", table_name="execution_queue", if_exists=True)
    op.drop_index("ix_execution_queue_requested_at", table_name="execution_queue", if_exists=True)
    op.drop_index("ix_execution_queue_request_batch_id", table_name="execution_queue", if_exists=True)
    op.drop_index("ix_execution_queue_requested_by", table_name="execution_queue", if_exists=True)
    op.drop_index("ix_execution_queue_prompt_id", table_name="execution_queue", if_exists=True)

    # Drop the table
    op.drop_table("execution_queue")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS executionqueuestatus")


def downgrade() -> None:
    # No downgrade - old system is permanently removed
    pass
