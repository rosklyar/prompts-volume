"""Integration tests for GSC functionality.

Tests the real user-facing GSC functionality:
1. Connecting GSC - OAuth flow stores credentials
2. Loading keywords - Fetch search analytics for property
3. Generating prompts - Convert keywords to prompts

External HTTP calls (Google OAuth, GSC API, OpenAI) are stubbed.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from src.config.settings import settings
from src.gsc.deps import get_oauth_service, get_token_manager
from src.gsc.services.oauth_service import OAuthService
from src.gsc.services.token_manager import TokenManager
from src.main import app


# ===== Test Configuration =====

# Generate a valid Fernet key for token encryption in tests
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


# ===== Mock Response Fixtures =====


@pytest.fixture
def mock_gsc_token_response():
    """Stub Google OAuth token exchange response."""
    return {
        "access_token": "mock-access-token",
        "refresh_token": "mock-refresh-token",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "https://www.googleapis.com/auth/webmasters.readonly",
    }


@pytest.fixture
def mock_gsc_sites_response():
    """Stub GSC sites list API response."""
    return {
        "siteEntry": [
            {"siteUrl": "sc-domain:example.com", "permissionLevel": "siteOwner"},
            {"siteUrl": "https://blog.example.com/", "permissionLevel": "siteFullUser"},
        ]
    }


@pytest.fixture
def mock_gsc_analytics_response():
    """Stub GSC search analytics API response.

    Includes both long-tail (3+ words) and short queries to test filtering.
    """
    return {
        "rows": [
            {
                "keys": ["best running shoes for flat feet"],
                "clicks": 100,
                "impressions": 1000,
                "ctr": 0.1,
                "position": 5.0,
            },
            {
                "keys": ["how to choose marathon running shoes"],
                "clicks": 80,
                "impressions": 800,
                "ctr": 0.1,
                "position": 3.0,
            },
            {
                "keys": ["running shoes"],  # Short query - should be filtered
                "clicks": 50,
                "impressions": 500,
                "ctr": 0.1,
                "position": 2.0,
            },
        ]
    }


@pytest.fixture
def oauth_service():
    """Create OAuth service with test settings."""
    return OAuthService(
        client_id="test-gsc-client-id",
        client_secret="test-gsc-client-secret",
        redirect_uri="http://localhost:8000/api/v1/gsc/auth/callback",
        secret_key=settings.secret_key,  # Use same key as app
    )


@pytest.fixture
def token_manager():
    """Create token manager with test encryption key."""
    return TokenManager(encryption_key=TEST_ENCRYPTION_KEY)


@pytest.fixture
def override_gsc_deps(oauth_service, token_manager):
    """Override GSC dependencies for testing."""
    app.dependency_overrides[get_oauth_service] = lambda: oauth_service
    app.dependency_overrides[get_token_manager] = lambda: token_manager
    yield
    app.dependency_overrides.pop(get_oauth_service, None)
    app.dependency_overrides.pop(get_token_manager, None)


# ===== Helper to create mock httpx responses =====


def _create_mock_response(status_code: int, json_data: dict | None = None, text: str = ""):
    """Create a mock httpx response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = text
    if json_data is not None:
        mock.json.return_value = json_data
    return mock


# ===== Helper to store test credentials =====


def _store_test_credentials(test_user, token_manager: TokenManager):
    """Store test GSC credentials for a user."""
    import asyncio

    import src.database.users_session as users_db_session
    from src.gsc.repository import GSCCredentialRepository

    async def _store():
        async with users_db_session._users_async_session_maker() as session:
            repo = GSCCredentialRepository(session)
            await repo.create(
                user_id=test_user.id,
                access_token_encrypted=token_manager.encrypt("mock-access-token"),
                refresh_token_encrypted=token_manager.encrypt("mock-refresh-token"),
                token_expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                scopes="https://www.googleapis.com/auth/webmasters.readonly",
            )
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_store())


# ===== GSC Connection Tests =====


class TestGSCConnection:
    """Tests for GSC OAuth connection flow."""

    def test_oauth_callback_stores_credentials(
        self, client, test_user, mock_gsc_token_response, oauth_service, override_gsc_deps
    ):
        """OAuth callback with valid code stores encrypted credentials.

        Stubs: Google OAuth token endpoint (httpx)
        Verifies: Credentials stored, redirect to frontend with success
        """
        # Generate valid state JWT using the same service the app uses
        state = oauth_service._create_state_jwt(str(test_user.id), None)

        # Mock token exchange
        mock_response = _create_mock_response(200, mock_gsc_token_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = client.get(
                "/api/v1/gsc/auth/callback",
                params={"code": "auth-code-from-google", "state": state},
                follow_redirects=False,
            )

        # Should redirect to frontend with success
        assert response.status_code == 307
        assert "gsc=connected" in response.headers["location"]

    def test_connection_status_returns_sites(
        self,
        client,
        auth_headers,
        test_user,
        mock_gsc_sites_response,
        token_manager,
        override_gsc_deps,
    ):
        """Connected user sees their GSC properties.

        Stubs: GSC sites API (httpx)
        Verifies: Status returns is_connected=True with sites list
        """
        # Store credentials for the user
        _store_test_credentials(test_user, token_manager)

        # Mock GSC sites API
        mock_response = _create_mock_response(200, mock_gsc_sites_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = client.get("/api/v1/gsc/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_connected"] is True
        assert len(data["sites"]) == 2
        assert data["sites"][0]["site_url"] == "sc-domain:example.com"


# ===== GSC Keyword Loading Tests =====


class TestGSCKeywordLoading:
    """Tests for loading keywords from GSC."""

    def test_search_analytics_returns_keywords(
        self,
        client,
        auth_headers,
        test_user,
        mock_gsc_analytics_response,
        token_manager,
        override_gsc_deps,
    ):
        """Fetching search analytics returns keyword data.

        Stubs: GSC search analytics API (httpx)
        Verifies: Returns keywords with clicks, impressions, CTR, position
        """
        # Store credentials
        _store_test_credentials(test_user, token_manager)

        # Mock GSC search analytics API
        mock_response = _create_mock_response(200, mock_gsc_analytics_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = client.post(
                "/api/v1/gsc/search-analytics",
                headers=auth_headers,
                json={
                    "site_url": "sc-domain:example.com",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-28",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "rows" in data
        assert len(data["rows"]) == 3
        # Verify first row has expected fields
        first_row = data["rows"][0]
        assert first_row["keys"] == ["best running shoes for flat feet"]
        assert first_row["clicks"] == 100
        assert first_row["impressions"] == 1000

    def test_extract_keywords_filters_short_queries(
        self,
        client,
        auth_headers,
        test_user,
        mock_gsc_analytics_response,
        token_manager,
        override_gsc_deps,
    ):
        """Keyword extraction filters out short queries (< 3 words).

        Stubs: GSC search analytics API (httpx)
        Verifies: Only long-tail keywords (3+ words) returned
        """
        # Store credentials
        _store_test_credentials(test_user, token_manager)

        # Mock GSC search analytics API
        mock_response = _create_mock_response(200, mock_gsc_analytics_response)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = client.post(
                "/onboarding/api/v1/gsc/extract-keywords",
                headers=auth_headers,
                json={
                    "site_url": "sc-domain:example.com",
                    "min_word_count": 3,
                    "result_limit": 10,
                },
            )

        assert response.status_code == 200
        data = response.json()
        # Should filter out "running shoes" (2 words)
        assert data["total_fetched"] == 3
        assert data["total_after_filter"] == 2
        # Verify only long-tail keywords returned
        keywords = data["keywords"]
        assert len(keywords) == 2
        assert keywords[0]["query"] == "best running shoes for flat feet"
        assert keywords[1]["query"] == "how to choose marathon running shoes"


# ===== GSC Prompt Generation Tests =====


class TestGSCPromptGeneration:
    """Tests for generating prompts from keywords."""

    def test_extract_keywords_with_prompt_generation(
        self,
        client,
        auth_headers,
        test_user,
        mock_gsc_analytics_response,
        token_manager,
        override_gsc_deps,
    ):
        """Keyword extraction with generate_prompts=True returns prompts.

        Stubs: GSC search analytics API (httpx), OpenAI API (prompt generator)
        Verifies: Returns keywords + generated prompts
        """
        # Store credentials
        _store_test_credentials(test_user, token_manager)

        # Mock GSC search analytics API
        mock_gsc_response = _create_mock_response(200, mock_gsc_analytics_response)

        # Create mock generator service
        mock_generator_service = MagicMock()
        mock_generator_service.generate_prompts_from_keywords = AsyncMock(
            return_value=[
                ("What are the best running shoes for flat feet?", "best running shoes for flat feet"),
                ("How do I choose marathon running shoes?", "how to choose marathon running shoes"),
            ]
        )

        with (
            patch("httpx.AsyncClient") as mock_httpx,
            patch(
                "src.onboarding.router.get_prompts_generator_service",
                return_value=mock_generator_service,
            ),
        ):
            # Setup httpx mock
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_gsc_response
            mock_httpx.return_value.__aenter__.return_value = mock_client

            response = client.post(
                "/onboarding/api/v1/gsc/extract-keywords",
                headers=auth_headers,
                json={
                    "site_url": "sc-domain:example.com",
                    "min_word_count": 3,
                    "result_limit": 10,
                    "generate_prompts": True,
                    "country_id": 1,  # USA from seed data
                },
            )

        assert response.status_code == 200
        data = response.json()
        # Should have generated prompts
        assert data["generated_prompts"] is not None
        assert len(data["generated_prompts"]) == 2
        assert data["generated_prompts"][0]["prompt"] == "What are the best running shoes for flat feet?"
        assert data["generated_prompts"][0]["source_keyword"] == "best running shoes for flat feet"

    def test_create_prompts_from_keywords_creates_group(self, client, auth_headers):
        """Creating prompts from keywords creates group with bound prompts.

        Stubs: None (prompts already extracted, no external calls)
        Verifies: Group created, prompts bound to group
        """
        response = client.post(
            "/onboarding/api/v1/gsc/create-prompts",
            headers=auth_headers,
            json={
                "prompts": [
                    "What are the best running shoes for flat feet?",
                    "How do I choose marathon running shoes?",
                ],
                "group_title": "Running Shoes Keywords",
                "country_id": 1,  # USA from seed data
                "brand": {
                    "name": "Nike",
                    "domain": "nike.com",
                    "variations": ["Nike Inc"],
                },
                "competitors": [
                    {"name": "Adidas", "domain": "adidas.com", "variations": []},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["group_title"] == "Running Shoes Keywords"
        assert data["prompts_created"] == 2
        assert len(data["prompt_ids"]) == 2

        # Verify group exists and has prompts
        group_response = client.get(
            f"/prompt-groups/api/v1/groups/{data['group_id']}",
            headers=auth_headers,
        )
        assert group_response.status_code == 200
        group_data = group_response.json()
        assert group_data["title"] == "Running Shoes Keywords"
        assert len(group_data["prompts"]) == 2
