"""add country_id and country_locked to prompt_groups

Revision ID: 009
Revises: 48bed8b3597f
Create Date: 2026-01-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, Sequence[str], None] = '48bed8b3597f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add country_id and country_locked columns to prompt_groups.

    Data migration:
    - Groups with topic: get country from topic.country_id, locked=true
    - Groups without topic: get Ukraine country_id, locked=false
    """
    # Step 1: Add columns as nullable first
    op.add_column('prompt_groups', sa.Column('country_id', sa.Integer(), nullable=True))
    op.add_column('prompt_groups', sa.Column('country_locked', sa.Boolean(), server_default='false', nullable=False))

    # Step 2: Populate country_id from topic or default to Ukraine
    # This uses raw SQL for data migration
    op.execute("""
        UPDATE prompt_groups pg
        SET country_id = COALESCE(
            (SELECT t.country_id FROM topics t WHERE t.id = pg.topic_id),
            (SELECT c.id FROM countries c WHERE c.iso_code = 'UA')
        ),
        country_locked = (pg.topic_id IS NOT NULL)
    """)

    # Step 3: Make country_id NOT NULL after data is populated
    op.alter_column('prompt_groups', 'country_id', nullable=False)

    # Step 4: Add foreign key constraint and index
    op.create_foreign_key(
        'fk_prompt_groups_country',
        'prompt_groups', 'countries',
        ['country_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_prompt_groups_country_id', 'prompt_groups', ['country_id'], unique=False)


def downgrade() -> None:
    """Remove country columns from prompt_groups."""
    op.drop_index('ix_prompt_groups_country_id', table_name='prompt_groups')
    op.drop_constraint('fk_prompt_groups_country', 'prompt_groups', type_='foreignkey')
    op.drop_column('prompt_groups', 'country_locked')
    op.drop_column('prompt_groups', 'country_id')
