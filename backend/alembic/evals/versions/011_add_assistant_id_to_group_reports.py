"""Add assistant_id to group_reports table

Revision ID: 011
Revises: 010
Create Date: 2026-01-22

Adds assistant_id column to group_reports for tracking which AI assistant
was used to generate each report. Defaults to 1 (ChatGPT) for existing reports.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, Sequence[str], None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add assistant_id column to group_reports."""
    op.add_column('group_reports', sa.Column(
        'assistant_id',
        sa.Integer(),
        nullable=False,
        server_default='1',  # Default to ChatGPT
    ))
    op.create_index(
        'ix_group_reports_assistant_id',
        'group_reports',
        ['assistant_id']
    )
    op.create_foreign_key(
        'fk_group_reports_assistant_id',
        'group_reports',
        'ai_assistants',
        ['assistant_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Remove assistant_id column from group_reports."""
    op.drop_constraint('fk_group_reports_assistant_id', 'group_reports', type_='foreignkey')
    op.drop_index('ix_group_reports_assistant_id', 'group_reports')
    op.drop_column('group_reports', 'assistant_id')
