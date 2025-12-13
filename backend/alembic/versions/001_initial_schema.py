"""Initial schema with all tables.

Revision ID: 001
Revises:
Create Date: 2025-01-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
    )

    # Create languages table
    op.create_table(
        "languages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("code", sa.String(10), nullable=False, unique=True, index=True),
    )

    # Create countries table
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("iso_code", sa.String(2), nullable=False, unique=True, index=True),
    )

    # Create country_languages junction table
    op.create_table(
        "country_languages",
        sa.Column(
            "country_id",
            sa.Integer(),
            sa.ForeignKey("countries.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "language_id",
            sa.Integer(),
            sa.ForeignKey("languages.id", ondelete="CASCADE"),
            primary_key=True,
        ),
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
        sa.Column(
            "business_domain_id",
            sa.Integer(),
            sa.ForeignKey("business_domains.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "country_id",
            sa.Integer(),
            sa.ForeignKey("countries.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    # Create prompts table with vector embedding
    op.create_table(
        "prompts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )

    # Create HNSW index for vector similarity search
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_prompt_embedding "
        "ON prompts USING hnsw (embedding vector_cosine_ops)"
    )

    # Create priority_prompt_queue table
    op.create_table(
        "priority_prompt_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prompt_id",
            sa.Integer(),
            sa.ForeignKey("prompts.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            index=True,
        ),
        sa.Column("request_id", sa.String(100), nullable=False, index=True),
    )

    # Create ai_assistants table
    op.create_table(
        "ai_assistants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Create ai_assistant_plans table
    op.create_table(
        "ai_assistant_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, index=True),
        sa.Column(
            "assistant_id",
            sa.Integer(),
            sa.ForeignKey("ai_assistants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("assistant_id", "name", name="uq_assistant_plan"),
    )

    # Create prompt_evaluations table
    op.create_table(
        "prompt_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prompt_id",
            sa.Integer(),
            sa.ForeignKey("prompts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "assistant_plan_id",
            sa.Integer(),
            sa.ForeignKey("ai_assistant_plans.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum("in_progress", "completed", "failed", name="evaluationstatus"),
            nullable=False,
            default="in_progress",
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            index=True,
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), nullable=True, index=True
        ),
        sa.Column("answer", sa.JSON(), nullable=True),
    )

    # Create prompt_groups table
    op.create_table(
        "prompt_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("user_id", "title", name="uq_prompt_groups_user_title"),
    )

    # Create prompt_group_bindings table
    op.create_table(
        "prompt_group_bindings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("prompt_groups.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "prompt_id",
            sa.Integer(),
            sa.ForeignKey("prompts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "group_id", "prompt_id", name="uq_prompt_group_bindings_group_prompt"
        ),
    )


def downgrade() -> None:
    op.drop_table("prompt_group_bindings")
    op.drop_table("prompt_groups")
    op.drop_table("prompt_evaluations")
    op.drop_table("ai_assistant_plans")
    op.drop_table("ai_assistants")
    op.drop_table("priority_prompt_queue")
    op.execute("DROP INDEX IF EXISTS idx_prompt_embedding")
    op.drop_table("prompts")
    op.drop_table("topics")
    op.drop_table("business_domains")
    op.drop_table("country_languages")
    op.drop_table("countries")
    op.drop_table("languages")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS evaluationstatus")
    op.execute("DROP EXTENSION IF EXISTS vector")
