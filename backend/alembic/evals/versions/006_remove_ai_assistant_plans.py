"""Remove ai_assistant_plans table and assistant_plan_id column.

Revision ID: 006
Revises: 005
Create Date: 2025-01-12

Finalizes the simplification from AIAssistant -> AIAssistantPlan -> PromptEvaluation
to the simpler AIAssistant -> PromptEvaluation model.

WARNING: This migration should only be applied AFTER migration 005 is confirmed
to work correctly in production. It is not reversible without data loss.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove assistant_plan_id column and ai_assistant_plans table."""
    # Step 1: Drop FK constraint from prompt_evaluations to ai_assistant_plans
    op.drop_constraint(
        "prompt_evaluations_assistant_plan_id_fkey",
        "prompt_evaluations",
        type_="foreignkey",
    )

    # Step 2: Drop partial index that references assistant_plan_id
    op.execute("DROP INDEX IF EXISTS idx_pe_poll_in_progress")

    # Step 3: Drop the assistant_plan_id index
    op.drop_index(
        "ix_prompt_evaluations_assistant_plan_id",
        table_name="prompt_evaluations",
        if_exists=True,
    )

    # Step 4: Drop assistant_plan_id column
    op.drop_column("prompt_evaluations", "assistant_plan_id")

    # Step 5: Drop ai_assistant_plans table (indexes will be dropped automatically)
    op.drop_table("ai_assistant_plans")


def downgrade() -> None:
    """Recreate ai_assistant_plans table and assistant_plan_id column.

    WARNING: This downgrade will NOT restore the data relationship.
    All evaluations will need to be manually re-associated with plans.
    """
    from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, text
    import sqlalchemy as sa

    # Step 1: Recreate ai_assistant_plans table
    op.create_table(
        "ai_assistant_plans",
        Column("id", Integer(), primary_key=True),
        Column("name", String(100), nullable=False),
        Column(
            "assistant_id",
            Integer(),
            ForeignKey("ai_assistants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
        ),
        UniqueConstraint("assistant_id", "name", name="uq_assistant_plan"),
    )
    op.create_index("ix_ai_assistant_plans_name", "ai_assistant_plans", ["name"])
    op.create_index("ix_ai_assistant_plans_assistant_id", "ai_assistant_plans", ["assistant_id"])

    # Step 2: Add assistant_plan_id column back (nullable initially)
    op.add_column(
        "prompt_evaluations",
        Column("assistant_plan_id", Integer(), nullable=True),
    )

    # Step 3: Create FK constraint
    op.create_foreign_key(
        "prompt_evaluations_assistant_plan_id_fkey",
        "prompt_evaluations",
        "ai_assistant_plans",
        ["assistant_plan_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Step 4: Create index
    op.create_index(
        "ix_prompt_evaluations_assistant_plan_id",
        "prompt_evaluations",
        ["assistant_plan_id"],
    )

    # Note: The column will be nullable and data needs to be manually populated
    # before making it NOT NULL
