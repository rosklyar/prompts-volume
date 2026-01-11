"""Add brightdata_batches table for tracking Bright Data scraping batches

Revision ID: 003
Revises: 002
Create Date: 2025-01-11

Adds a table to persist Bright Data batch information for webhook correlation.
Replaces the in-memory batch registry with database-backed storage.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create brightdata_batches table."""
    # Create brightdatabatchstatus enum
    op.execute("CREATE TYPE brightdatabatchstatus AS ENUM ('pending', 'completed', 'partial', 'failed')")
    brightdatabatchstatus_enum = postgresql.ENUM(
        "pending", "completed", "partial", "failed",
        name="brightdatabatchstatus",
        create_type=False
    )

    # Create brightdata_batches table
    op.create_table(
        "brightdata_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.String(36), nullable=False, unique=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("prompt_ids", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("status", brightdatabatchstatus_enum, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes
    op.create_index("ix_brightdata_batches_batch_id", "brightdata_batches", ["batch_id"], unique=True)
    op.create_index("ix_brightdata_batches_user_id", "brightdata_batches", ["user_id"])


def downgrade() -> None:
    """Drop brightdata_batches table."""
    op.drop_index("ix_brightdata_batches_user_id", table_name="brightdata_batches")
    op.drop_index("ix_brightdata_batches_batch_id", table_name="brightdata_batches")
    op.drop_table("brightdata_batches")
    op.execute("DROP TYPE IF EXISTS brightdatabatchstatus")
