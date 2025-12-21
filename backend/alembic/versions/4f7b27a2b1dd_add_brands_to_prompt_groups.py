"""add_brands_to_prompt_groups

Revision ID: 4f7b27a2b1dd
Revises: 002
Create Date: 2025-12-21 12:56:18.085360

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4f7b27a2b1dd'
down_revision: Union[str, Sequence[str], None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add brands JSONB column to prompt_groups table."""
    op.add_column(
        'prompt_groups',
        sa.Column('brands', postgresql.JSONB, nullable=True)
    )


def downgrade() -> None:
    """Remove brands column from prompt_groups table."""
    op.drop_column('prompt_groups', 'brands')
