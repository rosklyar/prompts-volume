"""add schedule columns to prompt_groups

Revision ID: 48bed8b3597f
Revises: 003
Create Date: 2026-01-15 23:43:18.574245

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48bed8b3597f'
down_revision: Union[str, Sequence[str], None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add schedule_enabled and schedule_last_run_at columns to prompt_groups."""
    op.add_column('prompt_groups', sa.Column('schedule_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('prompt_groups', sa.Column('schedule_last_run_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove schedule columns from prompt_groups."""
    op.drop_column('prompt_groups', 'schedule_last_run_at')
    op.drop_column('prompt_groups', 'schedule_enabled')
