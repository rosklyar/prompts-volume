"""Add admin setup tracking columns to user_preferences

Revision ID: 007
Revises: 006
Create Date: 2026-02-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, Sequence[str], None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add admin_setup_completed_at and admin_setup_by to user_preferences."""
    op.add_column(
        "user_preferences",
        sa.Column("admin_setup_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_preferences",
        sa.Column("admin_setup_by", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_user_preferences_admin_setup_completed_at",
        "user_preferences",
        ["admin_setup_completed_at"],
    )


def downgrade() -> None:
    """Remove admin setup tracking columns."""
    op.drop_index(
        "ix_user_preferences_admin_setup_completed_at",
        table_name="user_preferences",
    )
    op.drop_column("user_preferences", "admin_setup_by")
    op.drop_column("user_preferences", "admin_setup_completed_at")
