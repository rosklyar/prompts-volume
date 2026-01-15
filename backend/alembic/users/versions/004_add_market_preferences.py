"""Add default_country_id and default_business_domain_id to user_preferences

Revision ID: 004
Revises: 003
Create Date: 2026-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, Sequence[str], None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add market preference columns to user_preferences."""
    op.add_column(
        "user_preferences",
        sa.Column("default_country_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "user_preferences",
        sa.Column("default_business_domain_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Remove market preference columns from user_preferences."""
    op.drop_column("user_preferences", "default_business_domain_id")
    op.drop_column("user_preferences", "default_country_id")
