"""Remove unique constraint on group title per user

Revision ID: 003
Revises: 002
Create Date: 2025-01-15

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow duplicate group titles per user."""
    op.drop_constraint("uq_prompt_groups_user_title", "prompt_groups", type_="unique")


def downgrade() -> None:
    """Restore unique constraint on group title per user."""
    op.create_unique_constraint(
        "uq_prompt_groups_user_title", "prompt_groups", ["user_id", "title"]
    )
