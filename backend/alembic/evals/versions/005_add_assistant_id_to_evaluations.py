"""Add assistant_id to prompt_evaluations and brightdata_batches.

Revision ID: 005
Revises: 004
Create Date: 2025-01-12

Simplifies the data model by moving from AIAssistantPlan to AIAssistant directly.
Adds assistant_id column to prompt_evaluations (populated from existing data)
and to brightdata_batches for webhook correlation.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add assistant_id columns and migrate data."""
    # Step 1: Add nullable assistant_id column to prompt_evaluations
    op.add_column(
        "prompt_evaluations",
        sa.Column("assistant_id", sa.Integer(), nullable=True),
    )

    # Step 2: Populate assistant_id from existing data (join through ai_assistant_plans)
    # All existing evaluations have assistant_plan_id which links to ai_assistant_plans
    # which has assistant_id pointing to ai_assistants
    op.execute("""
        UPDATE prompt_evaluations pe
        SET assistant_id = ap.assistant_id
        FROM ai_assistant_plans ap
        WHERE pe.assistant_plan_id = ap.id
    """)

    # Step 3: Make assistant_id NOT NULL after population
    op.alter_column(
        "prompt_evaluations",
        "assistant_id",
        nullable=False,
    )

    # Step 4: Add FK constraint
    op.create_foreign_key(
        "fk_prompt_evaluations_assistant_id",
        "prompt_evaluations",
        "ai_assistants",
        ["assistant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Step 5: Create index for assistant_id queries
    op.create_index(
        "ix_prompt_evaluations_assistant_id",
        "prompt_evaluations",
        ["assistant_id"],
    )

    # Step 6: Add assistant_id to brightdata_batches for webhook correlation
    # Default to 1 (ChatGPT) for existing records
    op.add_column(
        "brightdata_batches",
        sa.Column("assistant_id", sa.Integer(), nullable=False, server_default="1"),
    )

    # Step 7: Add FK constraint for brightdata_batches.assistant_id
    op.create_foreign_key(
        "fk_brightdata_batches_assistant_id",
        "brightdata_batches",
        "ai_assistants",
        ["assistant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Step 8: Create index for brightdata_batches.assistant_id
    op.create_index(
        "ix_brightdata_batches_assistant_id",
        "brightdata_batches",
        ["assistant_id"],
    )


def downgrade() -> None:
    """Remove assistant_id columns."""
    # Drop from brightdata_batches
    op.drop_index("ix_brightdata_batches_assistant_id", table_name="brightdata_batches")
    op.drop_constraint("fk_brightdata_batches_assistant_id", "brightdata_batches", type_="foreignkey")
    op.drop_column("brightdata_batches", "assistant_id")

    # Drop from prompt_evaluations
    op.drop_index("ix_prompt_evaluations_assistant_id", table_name="prompt_evaluations")
    op.drop_constraint("fk_prompt_evaluations_assistant_id", "prompt_evaluations", type_="foreignkey")
    op.drop_column("prompt_evaluations", "assistant_id")
