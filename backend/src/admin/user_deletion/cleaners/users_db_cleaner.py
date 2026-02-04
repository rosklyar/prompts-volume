"""Cleaner for users_db tables."""

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.user_deletion.protocol import CleanupResult
from src.database.users_models import (
    BalanceTransaction,
    CreditGrant,
    GSCCredential,
    OAuthConnection,
    User,
    UserPreferences,
)


class UsersDbCleaner:
    """Cleans user data from users_db."""

    async def cleanup(self, user_id: str, session: AsyncSession) -> CleanupResult:
        """Delete all user-related data from users_db.

        Deletes:
        - OAuthConnection
        - GSCCredential
        - UserPreferences
        - CreditGrant
        - BalanceTransaction
        - User (hard delete)
        """
        deleted: dict[str, int] = {}

        # Delete OAuth connections
        oauth_result = await session.execute(
            delete(OAuthConnection).where(OAuthConnection.user_id == user_id)
        )
        deleted["oauth_connections"] = oauth_result.rowcount

        # Delete GSC credentials
        gsc_result = await session.execute(
            delete(GSCCredential).where(GSCCredential.user_id == user_id)
        )
        deleted["gsc_credentials"] = gsc_result.rowcount

        # Delete user preferences
        prefs_result = await session.execute(
            delete(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        deleted["user_preferences"] = prefs_result.rowcount

        # Delete credit grants
        grants_result = await session.execute(
            delete(CreditGrant).where(CreditGrant.user_id == user_id)
        )
        deleted["credit_grants"] = grants_result.rowcount

        # Delete balance transactions
        transactions_result = await session.execute(
            delete(BalanceTransaction).where(BalanceTransaction.user_id == user_id)
        )
        deleted["balance_transactions"] = transactions_result.rowcount

        # Hard delete the user
        user_result = await session.execute(
            delete(User).where(User.id == user_id)
        )
        deleted["users"] = user_result.rowcount

        return CleanupResult(database="users_db", deleted=deleted, orphaned={})
