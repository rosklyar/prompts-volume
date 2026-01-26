"""Add chunk retry tracking and report completeness

Revision ID: 013
Revises: 012
Create Date: 2026-01-26

Adds retry tracking columns to brightdata_batches for chunk-level retry mechanism.
Adds is_complete column to group_reports for completeness tracking.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, Sequence[str], None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add chunk retry and completeness tracking columns."""
    # Add retry tracking to brightdata_batches
    op.add_column('brightdata_batches', sa.Column(
        'retry_count',
        sa.Integer(),
        nullable=False,
        server_default='0',
    ))
    op.add_column('brightdata_batches', sa.Column(
        'max_retries',
        sa.Integer(),
        nullable=False,
        server_default='2',
    ))
    op.add_column('brightdata_batches', sa.Column(
        'first_submitted_at',
        sa.DateTime(timezone=True),
        nullable=True,
    ))
    op.add_column('brightdata_batches', sa.Column(
        'last_submitted_at',
        sa.DateTime(timezone=True),
        nullable=True,
    ))

    # Initialize submission timestamps for existing batches
    op.execute("""
        UPDATE brightdata_batches
        SET first_submitted_at = created_at,
            last_submitted_at = created_at
        WHERE first_submitted_at IS NULL
    """)

    # Add completeness tracking to group_reports
    op.add_column('group_reports', sa.Column(
        'is_complete',
        sa.Boolean(),
        nullable=False,
        server_default='true',
    ))


def downgrade() -> None:
    """Remove chunk retry and completeness tracking columns."""
    # Remove completeness tracking from group_reports
    op.drop_column('group_reports', 'is_complete')

    # Remove retry tracking from brightdata_batches
    op.drop_column('brightdata_batches', 'last_submitted_at')
    op.drop_column('brightdata_batches', 'first_submitted_at')
    op.drop_column('brightdata_batches', 'max_retries')
    op.drop_column('brightdata_batches', 'retry_count')
