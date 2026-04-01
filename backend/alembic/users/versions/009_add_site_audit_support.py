"""Add site audit support: status/progress columns + page results table

Revision ID: 009
Revises: 008
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, Sequence[str], None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add multi-page audit columns and page results table."""
    # Add new columns to geo_audit_results
    op.add_column(
        "geo_audit_results",
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'completed'")),
    )
    op.add_column(
        "geo_audit_results",
        sa.Column("pages_discovered", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "geo_audit_results",
        sa.Column("pages_audited", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "geo_audit_results",
        sa.Column("pages_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "geo_audit_results",
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    # Make score_total, score_rating, result_json nullable (pending audits don't have them yet)
    op.alter_column("geo_audit_results", "score_total", existing_type=sa.Float(), nullable=True)
    op.alter_column("geo_audit_results", "score_rating", existing_type=sa.String(20), nullable=True)
    op.alter_column("geo_audit_results", "result_json", existing_type=JSONB(), nullable=True)

    # Backfill existing rows
    op.execute(
        "UPDATE geo_audit_results SET status = 'completed', pages_total = 1, pages_audited = 1, pages_discovered = 1"
    )

    # Create page results table
    op.create_table(
        "geo_audit_page_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("audit_id", sa.Integer(), nullable=False),
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
        "ix_geo_audit_page_results_audit_id",
        "geo_audit_page_results",
        ["audit_id"],
    )


def downgrade() -> None:
    """Remove site audit support."""
    op.drop_index("ix_geo_audit_page_results_audit_id", table_name="geo_audit_page_results")
    op.drop_table("geo_audit_page_results")

    op.drop_column("geo_audit_results", "error_message")
    op.drop_column("geo_audit_results", "pages_total")
    op.drop_column("geo_audit_results", "pages_audited")
    op.drop_column("geo_audit_results", "pages_discovered")
    op.drop_column("geo_audit_results", "status")

    op.alter_column("geo_audit_results", "score_total", existing_type=sa.Float(), nullable=False)
    op.alter_column("geo_audit_results", "score_rating", existing_type=sa.String(20), nullable=False)
    op.alter_column("geo_audit_results", "result_json", existing_type=JSONB(), nullable=False)
