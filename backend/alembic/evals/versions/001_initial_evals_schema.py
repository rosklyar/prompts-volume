"""Initial evals_db schema

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
    """Create evals_db tables."""
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

    # Create priority_prompt_queue table (prompt_id is int reference, no FK)
    op.create_table(
        "priority_prompt_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt_id", sa.Integer(), nullable=False, unique=True),  # No FK - prompts in prompts_db
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("request_id", sa.String(100), nullable=False),
    )
    op.create_index("ix_priority_prompt_queue_prompt_id", "priority_prompt_queue", ["prompt_id"])
    op.create_index("ix_priority_prompt_queue_created_at", "priority_prompt_queue", ["created_at"])
    op.create_index("ix_priority_prompt_queue_request_id", "priority_prompt_queue", ["request_id"])

    # Create evaluationstatus enum
    op.execute("CREATE TYPE evaluationstatus AS ENUM ('in_progress', 'completed', 'failed')")
    evaluationstatus_enum = postgresql.ENUM("in_progress", "completed", "failed", name="evaluationstatus", create_type=False)

    # Create prompt_evaluations table (prompt_id is int reference, no FK)
    op.create_table(
        "prompt_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt_id", sa.Integer(), nullable=False),  # No FK - prompts in prompts_db
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

    # Create consumed_evaluations table
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
    op.execute("CREATE TYPE reportitemstatus AS ENUM ('included', 'awaiting', 'skipped')")
    reportitemstatus_enum = postgresql.ENUM("included", "awaiting", "skipped", name="reportitemstatus", create_type=False)

    # Create group_reports table (group_id is int reference, no FK)
    op.create_table(
        "group_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), nullable=False),  # No FK - prompt_groups in prompts_db
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

    # Create group_report_items table (prompt_id is int reference, no FK)
    op.create_table(
        "group_report_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("group_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_id", sa.Integer(), nullable=False),  # No FK - prompts in prompts_db
        sa.Column("evaluation_id", sa.Integer(), sa.ForeignKey("prompt_evaluations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", reportitemstatus_enum, nullable=False),
        sa.Column("is_fresh", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("amount_charged", sa.Numeric(12, 4), nullable=True),
    )
    op.create_index("ix_group_report_items_report_id", "group_report_items", ["report_id"])
    op.create_index("ix_group_report_items_prompt_id", "group_report_items", ["prompt_id"])
    op.create_index("ix_group_report_items_evaluation_id", "group_report_items", ["evaluation_id"])


def downgrade() -> None:
    """Drop evals_db tables."""
    op.drop_table("group_report_items")
    op.drop_table("group_reports")
    op.drop_table("consumed_evaluations")
    op.drop_table("prompt_evaluations")
    op.drop_table("priority_prompt_queue")
    op.drop_table("ai_assistant_plans")
    op.drop_table("ai_assistants")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS reportitemstatus")
    op.execute("DROP TYPE IF EXISTS evaluationstatus")
