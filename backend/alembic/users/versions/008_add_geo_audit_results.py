"""Add geo_audit_results table

Revision ID: 008
Revises: 007
Create Date: 2026-03-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, Sequence[str], None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create geo_audit_results table."""
    op.create_table(
        "geo_audit_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("score_total", sa.Float(), nullable=False),
        sa.Column("score_rating", sa.String(20), nullable=False),
        sa.Column("result_json", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_geo_audit_results_user_id",
        "geo_audit_results",
        ["user_id"],
    )
    op.create_index(
        "ix_geo_audit_results_created_at",
        "geo_audit_results",
        ["created_at"],
    )


def downgrade() -> None:
    """Drop geo_audit_results table."""
    op.drop_index("ix_geo_audit_results_created_at", table_name="geo_audit_results")
    op.drop_index("ix_geo_audit_results_user_id", table_name="geo_audit_results")
    op.drop_table("geo_audit_results")
