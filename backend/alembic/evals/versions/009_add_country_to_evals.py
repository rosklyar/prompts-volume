"""add country_id to evaluation models

Revision ID: 009
Revises: 008
Create Date: 2026-01-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, Sequence[str], None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Ukraine country_id from prompts_db seed data
UKRAINE_COUNTRY_ID = 1


def upgrade() -> None:
    """Add country_id to prompt_evaluations, group_reports, and brightdata_batches.

    Data migration: All existing records default to Ukraine (country_id=1).
    """
    # 1. Add country_id to prompt_evaluations
    op.add_column('prompt_evaluations', sa.Column(
        'country_id',
        sa.Integer(),
        nullable=False,
        server_default=str(UKRAINE_COUNTRY_ID)
    ))
    op.create_index(
        'ix_prompt_evaluations_country_id',
        'prompt_evaluations',
        ['country_id'],
        unique=False
    )
    # Add composite index for efficient lookups by (prompt, assistant, country)
    op.create_index(
        'ix_prompt_eval_prompt_assistant_country',
        'prompt_evaluations',
        ['prompt_id', 'assistant_id', 'country_id'],
        unique=False
    )

    # 2. Add country_id to group_reports
    op.add_column('group_reports', sa.Column(
        'country_id',
        sa.Integer(),
        nullable=False,
        server_default=str(UKRAINE_COUNTRY_ID)
    ))
    op.create_index(
        'ix_group_reports_country_id',
        'group_reports',
        ['country_id'],
        unique=False
    )

    # 3. Add country_id to brightdata_batches
    op.add_column('brightdata_batches', sa.Column(
        'country_id',
        sa.Integer(),
        nullable=False,
        server_default=str(UKRAINE_COUNTRY_ID)
    ))
    op.create_index(
        'ix_brightdata_batches_country_id',
        'brightdata_batches',
        ['country_id'],
        unique=False
    )


def downgrade() -> None:
    """Remove country_id from evaluation models."""
    # 1. Remove from brightdata_batches
    op.drop_index('ix_brightdata_batches_country_id', table_name='brightdata_batches')
    op.drop_column('brightdata_batches', 'country_id')

    # 2. Remove from group_reports
    op.drop_index('ix_group_reports_country_id', table_name='group_reports')
    op.drop_column('group_reports', 'country_id')

    # 3. Remove from prompt_evaluations
    op.drop_index('ix_prompt_eval_prompt_assistant_country', table_name='prompt_evaluations')
    op.drop_index('ix_prompt_evaluations_country_id', table_name='prompt_evaluations')
    op.drop_column('prompt_evaluations', 'country_id')
