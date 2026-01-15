"""Add prompt approval status for admin review workflow

Revision ID: 002
Revises: 001
Create Date: 2025-01-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add approval workflow fields to prompts and make topic_id nullable on prompt_groups."""
    # 1. Create enum type for approval status
    op.execute("CREATE TYPE promptapprovalstatus AS ENUM ('pending', 'approved', 'rejected')")

    # 2. Add approval columns to prompts table
    op.add_column(
        "prompts",
        sa.Column(
            "approval_status",
            sa.Enum("pending", "approved", "rejected", name="promptapprovalstatus"),
            nullable=False,
            server_default="approved",  # Existing prompts are approved
        ),
    )
    op.add_column(
        "prompts",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "prompts",
        sa.Column("reviewed_by", sa.String(36), nullable=True),
    )

    # 3. Create index on approval_status for efficient filtering
    op.create_index("ix_prompts_approval_status", "prompts", ["approval_status"])

    # 4. Make topic_id nullable on prompt_groups
    op.alter_column(
        "prompt_groups",
        "topic_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    """Remove approval workflow fields and restore topic_id NOT NULL constraint."""
    # Restore topic_id NOT NULL (requires all rows to have topic_id)
    op.alter_column(
        "prompt_groups",
        "topic_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Drop approval columns and index
    op.drop_index("ix_prompts_approval_status", "prompts")
    op.drop_column("prompts", "reviewed_by")
    op.drop_column("prompts", "reviewed_at")
    op.drop_column("prompts", "approval_status")

    # Drop enum type
    op.execute("DROP TYPE promptapprovalstatus")
