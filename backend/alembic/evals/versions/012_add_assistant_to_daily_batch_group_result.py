"""Add assistant_id to daily_batch_group_results

Revision ID: 012
Revises: 011
Create Date: 2026-01-25

Adds assistant_id column to daily_batch_group_results table.
This changes the cardinality from one result per group to one result per (group, assistant).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, Sequence[str], None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add assistant_id column to daily_batch_group_results."""
    op.add_column('daily_batch_group_results', sa.Column(
        'assistant_id',
        sa.Integer(),
        sa.ForeignKey('ai_assistants.id', ondelete='CASCADE'),
        nullable=False,
        server_default='1',  # Default to ChatGPT
    ))
    op.create_index(
        'ix_daily_batch_group_results_assistant_id',
        'daily_batch_group_results',
        ['assistant_id']
    )


def downgrade() -> None:
    """Remove assistant_id column from daily_batch_group_results."""
    op.drop_index('ix_daily_batch_group_results_assistant_id', table_name='daily_batch_group_results')
    op.drop_column('daily_batch_group_results', 'assistant_id')
