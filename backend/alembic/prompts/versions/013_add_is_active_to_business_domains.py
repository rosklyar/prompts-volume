"""Add is_active column to business_domains

Revision ID: 013
Revises: 012
Create Date: 2026-03-02

Adds is_active BOOLEAN NOT NULL DEFAULT true for soft-delete support.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "013"
down_revision: Union[str, Sequence[str], None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "business_domains",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("business_domains", "is_active")
