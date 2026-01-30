"""Tests for Google Search Console integration."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from cryptography.fernet import Fernet

from src.gsc.exceptions import (
    GSCConfigurationError,
    GSCInvalidStateError,
    GSCTokenRefreshError,
)
from src.gsc.models import GSCSiteInfo, TokenResponse
from src.gsc.services.token_manager import TokenManager
from src.gsc.services.oauth_service import OAuthService


# ===== Token Manager Tests =====


class TestTokenManager:
    """Tests for token encryption/decryption."""

    @pytest.fixture
    def encryption_key(self):
        """Generate a valid Fernet key for testing."""
        return Fernet.generate_key().decode()

    def test_encrypt_decrypt_roundtrip(self, encryption_key):
        """Token should be recoverable after encryption and decryption."""
        manager = TokenManager(encryption_key=encryption_key)
        original = "my-secret-access-token-12345"

        encrypted = manager.encrypt(original)
        decrypted = manager.decrypt(encrypted)

        assert decrypted == original
        assert encrypted != original  # Should be different

    def test_empty_encryption_key_raises(self):
        """Missing encryption key should raise configuration error."""
        with pytest.raises(GSCConfigurationError):
            TokenManager(encryption_key="")

    def test_invalid_encryption_key_raises(self):
        """Invalid Fernet key should raise configuration error."""
        with pytest.raises(GSCConfigurationError):
            TokenManager(encryption_key="not-a-valid-fernet-key")

    def test_is_token_expired_returns_true_when_expired(self, encryption_key):
        """Expired token should be detected."""
        manager = TokenManager(encryption_key=encryption_key)
        past = datetime.now(timezone.utc) - timedelta(hours=1)

        assert manager.is_token_expired(past) is True

    def test_is_token_expired_returns_true_within_buffer(self, encryption_key):
        """Token expiring within buffer window should be considered expired."""
        manager = TokenManager(encryption_key=encryption_key)
        # 3 minutes from now - within 5 minute buffer
        soon = datetime.now(timezone.utc) + timedelta(minutes=3)

        assert manager.is_token_expired(soon) is True

    def test_is_token_expired_returns_false_when_valid(self, encryption_key):
        """Valid token with sufficient time should not be expired."""
        manager = TokenManager(encryption_key=encryption_key)
        # 1 hour from now - well outside buffer
        future = datetime.now(timezone.utc) + timedelta(hours=1)

        assert manager.is_token_expired(future) is False

    def test_calculate_expiry(self, encryption_key):
        """Expiry calculation should be accurate."""
        manager = TokenManager(encryption_key=encryption_key)
        expires_in = 3600  # 1 hour

        before = datetime.now(timezone.utc)
        result = manager.calculate_expiry(expires_in)
        after = datetime.now(timezone.utc)

        # Result should be within expected range
        assert result >= before + timedelta(seconds=expires_in - 1)
        assert result <= after + timedelta(seconds=expires_in + 1)


# ===== OAuth Service Tests =====


class TestOAuthService:
    """Tests for OAuth flow handling."""

    @pytest.fixture
    def oauth_service(self):
        """Create OAuth service with test credentials."""
        return OAuthService(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost:8000/api/v1/gsc/auth/callback",
            secret_key="test-secret-key-for-jwt-signing",
        )

    def test_generate_auth_url_contains_required_params(self, oauth_service):
        """Auth URL should contain all required OAuth parameters."""
        url = oauth_service.generate_auth_url("user-123")

        assert "client_id=test-client-id" in url
        assert "redirect_uri=" in url
        assert "response_type=code" in url
        assert "scope=" in url
        assert "webmasters.readonly" in url
        assert "access_type=offline" in url
        assert "prompt=consent" in url
        assert "state=" in url

    def test_validate_state_extracts_user_id(self, oauth_service):
        """Valid state should return the encoded user ID."""
        user_id = "user-456"
        url = oauth_service.generate_auth_url(user_id)

        # Extract state from URL
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        state = params["state"][0]

        # Validate state
        extracted = oauth_service.validate_state(state)
        assert extracted == user_id

    def test_validate_state_rejects_tampered_state(self, oauth_service):
        """Tampered state should raise error."""
        with pytest.raises(GSCInvalidStateError):
            oauth_service.validate_state("invalid-jwt-token")

    def test_validate_state_rejects_expired_state(self, oauth_service):
        """Expired state should raise error."""
        import jwt
        from datetime import datetime, timezone, timedelta

        # Create an expired state
        expired_payload = {
            "sub": "user-789",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "purpose": "gsc_oauth",
        }
        expired_state = jwt.encode(
            expired_payload,
            "test-secret-key-for-jwt-signing",
            algorithm="HS256",
        )

        with pytest.raises(GSCInvalidStateError, match="expired"):
            oauth_service.validate_state(expired_state)

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, oauth_service):
        """Successful code exchange should return tokens."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "access-123",
            "refresh_token": "refresh-456",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await oauth_service.exchange_code("auth-code-xyz")

            assert result.access_token == "access-123"
            assert result.refresh_token == "refresh-456"
            assert result.expires_in == 3600

    @pytest.mark.asyncio
    async def test_exchange_code_failure_raises(self, oauth_service):
        """Failed code exchange should raise error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "invalid_grant"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(GSCTokenRefreshError):
                await oauth_service.exchange_code("invalid-code")

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, oauth_service):
        """Successful token refresh should return new tokens."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await oauth_service.refresh_access_token("old-refresh-token")

            assert result.access_token == "new-access-token"
            assert result.refresh_token is None  # Not always returned on refresh


# ===== Endpoint Tests =====


def test_gsc_status_requires_auth(client):
    """GSC status endpoint should require authentication."""
    response = client.get("/api/v1/gsc/status")
    assert response.status_code == 401


def test_gsc_disconnect_requires_auth(client):
    """GSC disconnect endpoint should require authentication."""
    response = client.delete("/api/v1/gsc/disconnect")
    assert response.status_code == 401


def test_gsc_initiate_auth_requires_auth(client):
    """GSC auth initiation should require authentication."""
    response = client.get("/api/v1/gsc/auth/initiate")
    assert response.status_code == 401


def test_gsc_status_not_connected(client, auth_headers):
    """GSC status should return not connected when no credentials stored."""
    from src.gsc.router import get_token_manager, get_oauth_service
    from src.gsc.services.token_manager import TokenManager
    from src.gsc.services.oauth_service import OAuthService
    from src.main import app

    # Create real mock objects that pass the dependency validation
    def mock_token_manager():
        return MagicMock(spec=TokenManager)

    def mock_oauth_service():
        return MagicMock(spec=OAuthService)

    # Override dependencies at FastAPI level
    app.dependency_overrides[get_token_manager] = mock_token_manager
    app.dependency_overrides[get_oauth_service] = mock_oauth_service

    try:
        response = client.get("/api/v1/gsc/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_connected"] is False
    finally:
        # Clean up overrides
        app.dependency_overrides.pop(get_token_manager, None)
        app.dependency_overrides.pop(get_oauth_service, None)


def test_gsc_disconnect_not_found_when_not_connected(client, auth_headers):
    """GSC disconnect should return 404 when not connected."""
    response = client.delete("/api/v1/gsc/disconnect", headers=auth_headers)
    assert response.status_code == 404


def test_gsc_search_analytics_requires_auth(client):
    """GSC search analytics endpoint should require authentication."""
    response = client.post(
        "/api/v1/gsc/search-analytics",
        json={
            "site_url": "sc-domain:example.com",
            "start_date": "2025-01-01",
            "end_date": "2025-01-28",
        },
    )
    assert response.status_code == 401


def test_gsc_search_analytics_not_connected(client, auth_headers):
    """GSC search analytics should return 400 when not connected."""
    from src.gsc.router import get_token_manager, get_oauth_service
    from src.gsc.services.token_manager import TokenManager
    from src.gsc.services.oauth_service import OAuthService
    from src.main import app

    def mock_token_manager():
        return MagicMock(spec=TokenManager)

    def mock_oauth_service():
        return MagicMock(spec=OAuthService)

    app.dependency_overrides[get_token_manager] = mock_token_manager
    app.dependency_overrides[get_oauth_service] = mock_oauth_service

    try:
        response = client.post(
            "/api/v1/gsc/search-analytics",
            headers=auth_headers,
            json={
                "site_url": "sc-domain:example.com",
                "start_date": "2025-01-01",
                "end_date": "2025-01-28",
            },
        )

        assert response.status_code == 400
        assert "not connected" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_token_manager, None)
        app.dependency_overrides.pop(get_oauth_service, None)
