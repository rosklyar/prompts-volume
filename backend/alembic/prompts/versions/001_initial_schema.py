"""Initial prompts_db schema

Revision ID: 001
Revises:
Create Date: 2024-12-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create prompts_db tables."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create languages table
    op.create_table(
        "languages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("code", sa.String(10), nullable=False, unique=True),
    )
    op.create_index("ix_languages_code", "languages", ["code"])

    # Create countries table
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("iso_code", sa.String(2), nullable=False, unique=True),
    )
    op.create_index("ix_countries_iso_code", "countries", ["iso_code"])

    # Create country_languages junction table
    op.create_table(
        "country_languages",
        sa.Column("country_id", sa.Integer(), sa.ForeignKey("countries.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("language_id", sa.Integer(), sa.ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("country_id", "order", name="uq_country_order"),
    )

    # Create business_domains table
    op.create_table(
        "business_domains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
    )

    # Create topics table
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("business_domain_id", sa.Integer(), sa.ForeignKey("business_domains.id", ondelete="CASCADE"), nullable=False),
        sa.Column("country_id", sa.Integer(), sa.ForeignKey("countries.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_topics_business_domain_id", "topics", ["business_domain_id"])
    op.create_index("ix_topics_country_id", "topics", ["country_id"])

    # Create prompts table with pgvector
    op.create_table(
        "prompts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=False),  # Will be cast to vector
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", sa.String(36), nullable=True),  # No FK - user is in users_db
    )
    op.create_index("ix_prompts_topic_id", "prompts", ["topic_id"])
    op.create_index("ix_prompts_user_id", "prompts", ["user_id"])

    # Alter embedding column to vector type
    op.execute("ALTER TABLE prompts ALTER COLUMN embedding TYPE vector(384) USING embedding::vector(384)")

    # Create HNSW index for vector similarity search
    op.execute(
        "CREATE INDEX ix_prompts_embedding_hnsw ON prompts "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # Create prompt_groups table (user_id is string reference, no FK - user is in users_db)
    op.create_table(
        "prompt_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column(
            "brand",
            postgresql.JSONB(),
            nullable=False,
            comment="Brand info: {name, domain, variations}"
        ),
        sa.Column(
            "competitors",
            postgresql.JSONB(),
            nullable=True,
            comment="Competitors: [{name, domain, variations}, ...]"
        ),
        sa.UniqueConstraint("user_id", "title", name="uq_prompt_groups_user_title"),
    )
    op.create_index("ix_prompt_groups_user_id", "prompt_groups", ["user_id"])
    op.create_index("ix_prompt_groups_topic_id", "prompt_groups", ["topic_id"])

    # Create prompt_group_bindings table
    op.create_table(
        "prompt_group_bindings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("prompt_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_id", sa.Integer(), sa.ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("group_id", "prompt_id", name="uq_prompt_group_bindings_group_prompt"),
    )
    op.create_index("ix_prompt_group_bindings_group_id", "prompt_group_bindings", ["group_id"])
    op.create_index("ix_prompt_group_bindings_prompt_id", "prompt_group_bindings", ["prompt_id"])


def downgrade() -> None:
    """Drop all prompts_db tables."""
    op.drop_table("prompt_group_bindings")
    op.drop_table("prompt_groups")
    op.drop_table("prompts")
    op.drop_table("topics")
    op.drop_table("business_domains")
    op.drop_table("country_languages")
    op.drop_table("countries")
    op.drop_table("languages")

    # Drop pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector")
