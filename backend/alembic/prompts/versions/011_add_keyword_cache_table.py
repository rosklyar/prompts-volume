"""Add keyword_cache table

Revision ID: 011
Revises: 010
Create Date: 2026-02-23

Adds keyword_cache table for caching DataForSEO ranked keywords per domain.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "011"
down_revision: Union[str, Sequence[str], None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "keyword_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False, index=True),
        sa.Column("country_code", sa.String(10), nullable=False),
        sa.Column("language_name", sa.String(100), nullable=False),
        sa.Column(
            "keywords_data",
            JSONB(),
            nullable=False,
            comment="[{keyword, search_volume, rank_group}, ...]",
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "domain",
            "country_code",
            "language_name",
            name="uq_keyword_cache_domain_country_lang",
        ),
    )


def downgrade() -> None:
    op.drop_table("keyword_cache")
