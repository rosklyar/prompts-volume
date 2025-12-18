"""Remove common groups concept.

Revision ID: 002
Revises: 001
Create Date: 2025-01-01

This migration:
1. Deletes all common groups (title IS NULL) and their bindings (cascade)
2. Makes the title column NOT NULL
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delete common groups (title IS NULL) - bindings cascade delete
    op.execute("DELETE FROM prompt_groups WHERE title IS NULL")

    # Make title column NOT NULL
    op.alter_column(
        "prompt_groups",
        "title",
        existing_type=sa.String(255),
        nullable=False,
    )


def downgrade() -> None:
    # Make title column nullable again
    op.alter_column(
        "prompt_groups",
        "title",
        existing_type=sa.String(255),
        nullable=True,
    )
