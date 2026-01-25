"""Add schedule_assistant_ids column to prompt_groups

Revision ID: 010
Revises: 009
Create Date: 2026-01-25

Adds schedule_assistant_ids ARRAY(Integer) column to prompt_groups table
to store which assistants should be used for scheduled runs.

Data migration: Existing groups with schedule_enabled=True get ChatGPT (id=1) as default.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, Sequence[str], None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add schedule_assistant_ids column and migrate existing data."""
    # 1. Add column (nullable initially)
    op.add_column('prompt_groups', sa.Column(
        'schedule_assistant_ids',
        ARRAY(sa.Integer()),
        nullable=True,
        comment='Assistant IDs for scheduled runs. NULL = disabled'
    ))

    # 2. Set existing scheduled groups to ChatGPT (id=1)
    op.execute("""
        UPDATE prompt_groups
        SET schedule_assistant_ids = ARRAY[1]
        WHERE schedule_enabled = true
    """)


def downgrade() -> None:
    """Remove schedule_assistant_ids column."""
    op.drop_column('prompt_groups', 'schedule_assistant_ids')
