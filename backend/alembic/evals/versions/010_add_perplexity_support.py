"""Add Perplexity AI assistant and index_to_prompt_id column

Revision ID: 010
Revises: 009
Create Date: 2026-01-21

Adds:
- Perplexity AI assistant (ID=2) to ai_assistants table
- index_to_prompt_id JSON column to brightdata_batches for reliable webhook matching
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, Sequence[str], None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Perplexity assistant and index_to_prompt_id column."""
    # 1. Add index_to_prompt_id column to brightdata_batches
    op.add_column('brightdata_batches', sa.Column(
        'index_to_prompt_id',
        sa.JSON(),
        nullable=True,
        comment='Map of 1-based index to prompt_id for webhook matching'
    ))

    # 2. Insert Perplexity AI assistant
    op.execute("""
        INSERT INTO ai_assistants (id, name)
        VALUES (2, 'Perplexity')
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    """Remove Perplexity assistant and index_to_prompt_id column."""
    # 1. Remove index_to_prompt_id column
    op.drop_column('brightdata_batches', 'index_to_prompt_id')

    # 2. Remove Perplexity assistant
    op.execute("DELETE FROM ai_assistants WHERE id = 2")
