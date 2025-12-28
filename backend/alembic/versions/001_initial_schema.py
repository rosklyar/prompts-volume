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
    )
    op.create_index("ix_prompts_topic_id", "prompts", ["topic_id"])

    # Alter embedding column to vector type
    op.execute("ALTER TABLE prompts ALTER COLUMN embedding TYPE vector(384) USING embedding::vector(384)")

    # Create HNSW index for vector similarity search
    op.execute(
        "CREATE INDEX ix_prompts_embedding_hnsw ON prompts "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # Create priority_prompt_queue table
    op.create_table(
        "priority_prompt_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt_id", sa.Integer(), sa.ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("request_id", sa.String(100), nullable=False),
    )
    op.create_index("ix_priority_prompt_queue_prompt_id", "priority_prompt_queue", ["prompt_id"])
    op.create_index("ix_priority_prompt_queue_created_at", "priority_prompt_queue", ["created_at"])
    op.create_index("ix_priority_prompt_queue_request_id", "priority_prompt_queue", ["request_id"])

    # Create ai_assistants table
    op.create_table(
        "ai_assistants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ai_assistants_name", "ai_assistants", ["name"])

    # Create ai_assistant_plans table
    op.create_table(
        "ai_assistant_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("assistant_id", sa.Integer(), sa.ForeignKey("ai_assistants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("assistant_id", "name", name="uq_assistant_plan"),
    )
    op.create_index("ix_ai_assistant_plans_name", "ai_assistant_plans", ["name"])
    op.create_index("ix_ai_assistant_plans_assistant_id", "ai_assistant_plans", ["assistant_id"])

    # Create prompt_evaluations table (enum will be created automatically by SQLAlchemy)
    evaluationstatus_enum = postgresql.ENUM("in_progress", "completed", "failed", name="evaluationstatus", create_type=False)
    op.execute("CREATE TYPE evaluationstatus AS ENUM ('in_progress', 'completed', 'failed')")

    op.create_table(
        "prompt_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt_id", sa.Integer(), sa.ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assistant_plan_id", sa.Integer(), sa.ForeignKey("ai_assistant_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", evaluationstatus_enum, nullable=False, server_default="in_progress"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answer", postgresql.JSON(), nullable=True),
    )
    op.create_index("ix_prompt_evaluations_prompt_id", "prompt_evaluations", ["prompt_id"])
    op.create_index("ix_prompt_evaluations_assistant_plan_id", "prompt_evaluations", ["assistant_plan_id"])
    op.create_index("ix_prompt_evaluations_status", "prompt_evaluations", ["status"])
    op.create_index("ix_prompt_evaluations_created_at", "prompt_evaluations", ["created_at"])
    op.create_index("ix_prompt_evaluations_completed_at", "prompt_evaluations", ["completed_at"])

    # Create prompt_groups table (user_id is now just a string, no FK)
    op.create_table(
        "prompt_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),  # No FK - user is in users_db
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("brands", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("user_id", "title", name="uq_prompt_groups_user_title"),
    )
    op.create_index("ix_prompt_groups_user_id", "prompt_groups", ["user_id"])

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

    # Create consumed_evaluations table (user_id is now just a string, no FK)
    op.create_table(
        "consumed_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),  # No FK - user is in users_db
        sa.Column("evaluation_id", sa.Integer(), sa.ForeignKey("prompt_evaluations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount_charged", sa.Numeric(12, 4), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "evaluation_id", name="uq_consumed_eval_user_eval"),
    )
    op.create_index("ix_consumed_evaluations_user_id", "consumed_evaluations", ["user_id"])
    op.create_index("ix_consumed_evaluations_evaluation_id", "consumed_evaluations", ["evaluation_id"])

    # Create reportitemstatus enum
    reportitemstatus_enum = postgresql.ENUM("included", "awaiting", "skipped", name="reportitemstatus", create_type=False)
    op.execute("CREATE TYPE reportitemstatus AS ENUM ('included', 'awaiting', 'skipped')")

    # Create group_reports table (user_id is now just a string, no FK)
    op.create_table(
        "group_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("prompt_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),  # No FK - user is in users_db
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("total_prompts", sa.Integer(), nullable=False),
        sa.Column("prompts_with_data", sa.Integer(), nullable=False),
        sa.Column("prompts_awaiting", sa.Integer(), nullable=False),
        sa.Column("total_evaluations_loaded", sa.Integer(), nullable=False),
        sa.Column("total_cost", sa.Numeric(12, 4), nullable=False),
    )
    op.create_index("ix_group_reports_group_id", "group_reports", ["group_id"])
    op.create_index("ix_group_reports_user_id", "group_reports", ["user_id"])
    op.create_index("ix_group_reports_created_at", "group_reports", ["created_at"])

    # Create group_report_items table
    op.create_table(
        "group_report_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("group_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_id", sa.Integer(), sa.ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evaluation_id", sa.Integer(), sa.ForeignKey("prompt_evaluations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", reportitemstatus_enum, nullable=False),
        sa.Column("is_fresh", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("amount_charged", sa.Numeric(12, 4), nullable=True),
    )
    op.create_index("ix_group_report_items_report_id", "group_report_items", ["report_id"])
    op.create_index("ix_group_report_items_prompt_id", "group_report_items", ["prompt_id"])
    op.create_index("ix_group_report_items_evaluation_id", "group_report_items", ["evaluation_id"])


def downgrade() -> None:
    """Drop all prompts_db tables."""
    op.drop_table("group_report_items")
    op.drop_table("group_reports")
    op.drop_table("consumed_evaluations")
    op.drop_table("prompt_group_bindings")
    op.drop_table("prompt_groups")
    op.drop_table("prompt_evaluations")
    op.drop_table("ai_assistant_plans")
    op.drop_table("ai_assistants")
    op.drop_table("priority_prompt_queue")
    op.drop_table("prompts")
    op.drop_table("topics")
    op.drop_table("business_domains")
    op.drop_table("country_languages")
    op.drop_table("countries")
    op.drop_table("languages")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS reportitemstatus")
    op.execute("DROP TYPE IF EXISTS evaluationstatus")

    # Drop pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector")
