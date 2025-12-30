"""Initial users_db schema

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
    """Create users_db tables."""
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])

    # Create creditsource enum
    op.execute("CREATE TYPE creditsource AS ENUM ('signup_bonus', 'payment', 'promo_code', 'referral', 'admin_grant')")
    creditsource_enum = postgresql.ENUM(
        "signup_bonus", "payment", "promo_code", "referral", "admin_grant",
        name="creditsource", create_type=False
    )

    # Create credit_grants table
    op.create_table(
        "credit_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("source", creditsource_enum, nullable=False),
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

    # Create transactiontype enum
    op.execute("CREATE TYPE transactiontype AS ENUM ('debit', 'credit')")
    transactiontype_enum = postgresql.ENUM("debit", "credit", name="transactiontype", create_type=False)

    # Create balance_transactions table
    op.create_table(
        "balance_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("transaction_type", transactiontype_enum, nullable=False),
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
    op.create_index("ix_balance_transactions_user_id", "balance_transactions", ["user_id"])
    op.create_index("ix_balance_transactions_created_at", "balance_transactions", ["created_at"])


def downgrade() -> None:
    """Drop users_db tables."""
    op.drop_table("balance_transactions")
    op.drop_table("credit_grants")
    op.drop_table("users")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS transactiontype")
    op.execute("DROP TYPE IF EXISTS creditsource")
