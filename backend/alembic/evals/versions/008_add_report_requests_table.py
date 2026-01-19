"""add report_requests table

Revision ID: 008
Revises: 7441615a88ca
Create Date: 2026-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, Sequence[str], None] = '7441615a88ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create report_requests table for unified manual/scheduled reports."""
    # Create enum type
    op.execute("CREATE TYPE reportrequeststatus AS ENUM ('awaiting', 'ready', 'generating', 'completed', 'timed_out', 'cancelled')")

    # Create report_requests table
    op.create_table('report_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('assistant_id', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('awaiting', 'ready', 'generating', 'completed', 'timed_out', 'cancelled', name='reportrequeststatus', create_type=False), nullable=False),
        sa.Column('batch_ids', postgresql.ARRAY(sa.String(length=36)), nullable=False),
        sa.Column('fresh_prompt_selections', sa.JSON(), nullable=True, comment='Map of prompt_id -> evaluation_id for prompts that were fresh at request time'),
        sa.Column('total_prompts', sa.Integer(), nullable=False),
        sa.Column('prompts_fresh_at_request', sa.Integer(), nullable=False),
        sa.Column('prompts_requested', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('timeout_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('daily_batch_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['assistant_id'], ['ai_assistants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['daily_batch_id'], ['daily_schedule_batches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['report_id'], ['group_reports.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_report_requests_group_id', 'report_requests', ['group_id'], unique=False)
    op.create_index('ix_report_requests_user_id', 'report_requests', ['user_id'], unique=False)
    op.create_index('ix_report_requests_assistant_id', 'report_requests', ['assistant_id'], unique=False)
    op.create_index('ix_report_requests_report_id', 'report_requests', ['report_id'], unique=False)
    op.create_index('ix_report_requests_created_at', 'report_requests', ['created_at'], unique=False)
    op.create_index('ix_report_requests_daily_batch_id', 'report_requests', ['daily_batch_id'], unique=False)


def downgrade() -> None:
    """Drop report_requests table."""
    op.drop_index('ix_report_requests_daily_batch_id', table_name='report_requests')
    op.drop_index('ix_report_requests_created_at', table_name='report_requests')
    op.drop_index('ix_report_requests_report_id', table_name='report_requests')
    op.drop_index('ix_report_requests_assistant_id', table_name='report_requests')
    op.drop_index('ix_report_requests_user_id', table_name='report_requests')
    op.drop_index('ix_report_requests_group_id', table_name='report_requests')
    op.drop_table('report_requests')
    op.execute("DROP TYPE reportrequeststatus")
