"""add_billing_and_report_tables

Revision ID: 003
Revises: 4f7b27a2b1dd
Create Date: 2025-12-25 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "4f7b27a2b1dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add billing and report tables."""

    # Create creditsource enum
    op.execute(
        """
        CREATE TYPE creditsource AS ENUM (
            'signup_bonus', 'payment', 'promo_code', 'referral', 'admin_grant'
        )
        """
    )

    # Create transactiontype enum
    op.execute(
        """
        CREATE TYPE transactiontype AS ENUM ('debit', 'credit')
        """
    )

    # Create reportitemstatus enum
    op.execute(
        """
        CREATE TYPE reportitemstatus AS ENUM ('included', 'awaiting', 'skipped')
        """
    )

    # Create credit_grants table
    op.create_table(
        "credit_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum(
                "signup_bonus",
                "payment",
                "promo_code",
                "referral",
                "admin_grant",
                name="creditsource",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("original_amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("remaining_amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_credit_grants_user_id", "credit_grants", ["user_id"])
    op.create_index("ix_credit_grants_expires_at", "credit_grants", ["expires_at"])

    # Create balance_transactions table
    op.create_table(
        "balance_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "transaction_type",
            sa.Enum("debit", "credit", name="transactiontype", create_type=False),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 4), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_balance_transactions_user_id", "balance_transactions", ["user_id"]
    )
    op.create_index(
        "ix_balance_transactions_created_at", "balance_transactions", ["created_at"]
    )

    # Create consumed_evaluations table
    op.create_table(
        "consumed_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evaluation_id",
            sa.Integer(),
            sa.ForeignKey("prompt_evaluations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount_charged", sa.Numeric(12, 4), nullable=False),
        sa.Column(
            "consumed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "user_id", "evaluation_id", name="uq_consumed_eval_user_eval"
        ),
    )
    op.create_index(
        "ix_consumed_evaluations_user_id", "consumed_evaluations", ["user_id"]
    )
    op.create_index(
        "ix_consumed_evaluations_evaluation_id",
        "consumed_evaluations",
        ["evaluation_id"],
    )

    # Create group_reports table
    op.create_table(
        "group_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("prompt_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
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
        sa.Column(
            "report_id",
            sa.Integer(),
            sa.ForeignKey("group_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prompt_id",
            sa.Integer(),
            sa.ForeignKey("prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evaluation_id",
            sa.Integer(),
            sa.ForeignKey("prompt_evaluations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "included",
                "awaiting",
                "skipped",
                name="reportitemstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("is_fresh", sa.Boolean(), nullable=False, default=False),
        sa.Column("amount_charged", sa.Numeric(12, 4), nullable=True),
    )
    op.create_index(
        "ix_group_report_items_report_id", "group_report_items", ["report_id"]
    )
    op.create_index(
        "ix_group_report_items_prompt_id", "group_report_items", ["prompt_id"]
    )
    op.create_index(
        "ix_group_report_items_evaluation_id", "group_report_items", ["evaluation_id"]
    )


def downgrade() -> None:
    """Remove billing and report tables."""
    op.drop_table("group_report_items")
    op.drop_table("group_reports")
    op.drop_table("consumed_evaluations")
    op.drop_table("balance_transactions")
    op.drop_table("credit_grants")

    op.execute("DROP TYPE reportitemstatus")
    op.execute("DROP TYPE transactiontype")
    op.execute("DROP TYPE creditsource")
