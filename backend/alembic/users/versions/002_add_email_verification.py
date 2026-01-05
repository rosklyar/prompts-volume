"""Add email verification fields

Revision ID: 002
Revises: 001
Create Date: 2026-01-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email verification columns to users table."""
    # Add email_verified column (default false for new users)
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
    )
    # Add verification token column (stores SHA-256 hash, 64 hex chars)
    op.add_column(
        "users",
        sa.Column("email_verification_token", sa.String(64), nullable=True),
    )
    # Add token expiry column
    op.add_column(
        "users",
        sa.Column("email_verification_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Create unique index on verification token for fast lookups
    op.create_index(
        "ix_users_email_verification_token",
        "users",
        ["email_verification_token"],
        unique=True,
    )

    # Mark all existing users as verified (backward compatibility)
    op.execute("UPDATE users SET email_verified = true")


def downgrade() -> None:
    """Remove email verification columns from users table."""
    op.drop_index("ix_users_email_verification_token", table_name="users")
    op.drop_column("users", "email_verification_token_expires_at")
    op.drop_column("users", "email_verification_token")
    op.drop_column("users", "email_verified")
