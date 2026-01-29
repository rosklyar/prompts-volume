"""OAuth user resolution - links OAuth identities to local users."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import crud
from src.auth.oauth.protocols import OAuthUserInfo
from src.auth.oauth.repository import OAuthConnectionRepository
from src.database.users_models import CreditGrant, CreditSource, User


@dataclass
class OAuthResolution:
    """Result of resolving an OAuth identity to a local user.

    Attributes:
        user: The resolved or created user
        action: What action was taken
            - "existing_oauth": User logged in via existing OAuth connection
            - "linked": OAuth connected to existing email-matched user
            - "created": New user created from OAuth identity
    """

    user: User
    action: Literal["existing_oauth", "linked", "created"]


class OAuthUserResolver:
    """Resolves OAuth identities to local users.

    Handles three scenarios:
    1. Existing OAuth connection -> return user
    2. Email matches existing user -> link OAuth and return user
    3. No match -> create new user with OAuth connection

    Open for extension: subclass to change user creation policy.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        signup_credits: float,
        signup_credits_expiry_days: int,
        max_signup_bonuses: int | None,
    ):
        self._session = session
        self._oauth_repo = OAuthConnectionRepository(session)
        self._signup_credits = signup_credits
        self._signup_credits_expiry_days = signup_credits_expiry_days
        self._max_signup_bonuses = max_signup_bonuses

    async def resolve(self, oauth_info: OAuthUserInfo) -> OAuthResolution:
        """Resolve OAuth identity to a local user.

        Args:
            oauth_info: Validated OAuth user information

        Returns:
            OAuthResolution with user and action taken
        """
        # 1. Check for existing OAuth connection
        existing_connection = await self._oauth_repo.find_by_provider_user_id(
            oauth_info.provider,
            oauth_info.provider_user_id,
        )

        if existing_connection:
            user = await self._session.get(User, existing_connection.user_id)
            if user and not user.is_deleted:
                await self._oauth_repo.update_last_login(existing_connection)
                return OAuthResolution(user=user, action="existing_oauth")

        # 2. Check if email matches existing user
        existing_user = await crud.get_user_by_email(self._session, oauth_info.email)

        if existing_user and not existing_user.is_deleted:
            # Link OAuth to existing user
            await self._oauth_repo.create(
                user_id=existing_user.id,
                provider=oauth_info.provider,
                provider_user_id=oauth_info.provider_user_id,
                provider_email=oauth_info.email,
            )
            # Mark email as verified (Google verified it)
            if not existing_user.email_verified:
                existing_user.email_verified = True
                existing_user.is_active = True
                self._session.add(existing_user)
            return OAuthResolution(user=existing_user, action="linked")

        # 3. Create new user
        new_user = await self._create_oauth_user(oauth_info)
        await self._oauth_repo.create(
            user_id=new_user.id,
            provider=oauth_info.provider,
            provider_user_id=oauth_info.provider_user_id,
            provider_email=oauth_info.email,
        )
        return OAuthResolution(user=new_user, action="created")

    async def _create_oauth_user(self, oauth_info: OAuthUserInfo) -> User:
        """Create a new user from OAuth identity.

        Override this method to customize user creation policy.
        """
        user = User(
            email=oauth_info.email,
            hashed_password=None,  # No password for OAuth-only users
            full_name=oauth_info.full_name,
            is_active=True,
            is_superuser=False,
            email_verified=True,  # OAuth provider verified email
        )
        self._session.add(user)
        await self._session.flush()  # Get user ID

        # Grant signup credits if limit not reached
        if (
            self._max_signup_bonuses is None
            or await crud.count_signup_bonuses(self._session) < self._max_signup_bonuses
        ):
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=self._signup_credits_expiry_days
            )
            credit_grant = CreditGrant(
                user_id=user.id,
                source=CreditSource.SIGNUP_BONUS,
                original_amount=Decimal(str(self._signup_credits)),
                remaining_amount=Decimal(str(self._signup_credits)),
                expires_at=expires_at,
            )
            self._session.add(credit_grant)

        return user
