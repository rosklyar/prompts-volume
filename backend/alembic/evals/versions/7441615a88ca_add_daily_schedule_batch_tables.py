"""add daily schedule batch tables

Revision ID: 7441615a88ca
Revises: 006
Create Date: 2026-01-15 23:43:22.537716

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7441615a88ca'
down_revision: Union[str, Sequence[str], None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create daily_schedule_batches and daily_batch_group_results tables."""
    # Create enum types
    op.execute("CREATE TYPE dailybatchstatus AS ENUM ('collecting', 'requesting', 'awaiting', 'generating', 'completed', 'failed')")
    op.execute("CREATE TYPE dailybatchgroupstatus AS ENUM ('pending', 'completed', 'failed')")

    # Create daily_schedule_batches table
    op.create_table('daily_schedule_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('status', postgresql.ENUM('collecting', 'requesting', 'awaiting', 'generating', 'completed', 'failed', name='dailybatchstatus', create_type=False), nullable=False),
        sa.Column('batch_ids', postgresql.ARRAY(sa.String(length=36)), nullable=False),
        sa.Column('group_ids', postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column('total_prompts', sa.Integer(), nullable=False),
        sa.Column('prompts_needing_refresh', sa.Integer(), nullable=False),
        sa.Column('prompts_already_fresh', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('timeout_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_daily_schedule_batches_scheduled_date', 'daily_schedule_batches', ['scheduled_date'], unique=True)

    # Create daily_batch_group_results table
    op.create_table('daily_batch_group_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'completed', 'failed', name='dailybatchgroupstatus', create_type=False), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=True),
        sa.Column('prompts_in_group', sa.Integer(), nullable=False),
        sa.Column('prompts_needing_refresh', sa.Integer(), nullable=False),
        sa.Column('prompts_already_fresh', sa.Integer(), nullable=False),
        sa.Column('fresh_prompt_selections', sa.JSON(), nullable=True, comment='Map of prompt_id -> evaluation_id for prompts that were fresh at scheduling time'),
        sa.ForeignKeyConstraint(['batch_id'], ['daily_schedule_batches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['report_id'], ['group_reports.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_daily_batch_group_results_batch_id', 'daily_batch_group_results', ['batch_id'], unique=False)
    op.create_index('ix_daily_batch_group_results_group_id', 'daily_batch_group_results', ['group_id'], unique=False)
    op.create_index('ix_daily_batch_group_results_report_id', 'daily_batch_group_results', ['report_id'], unique=False)
    op.create_index('ix_daily_batch_group_results_user_id', 'daily_batch_group_results', ['user_id'], unique=False)


def downgrade() -> None:
    """Drop daily schedule batch tables."""
    op.drop_index('ix_daily_batch_group_results_user_id', table_name='daily_batch_group_results')
    op.drop_index('ix_daily_batch_group_results_report_id', table_name='daily_batch_group_results')
    op.drop_index('ix_daily_batch_group_results_group_id', table_name='daily_batch_group_results')
    op.drop_index('ix_daily_batch_group_results_batch_id', table_name='daily_batch_group_results')
    op.drop_table('daily_batch_group_results')
    op.drop_index('ix_daily_schedule_batches_scheduled_date', table_name='daily_schedule_batches')
    op.drop_table('daily_schedule_batches')
    op.execute("DROP TYPE dailybatchgroupstatus")
    op.execute("DROP TYPE dailybatchstatus")
