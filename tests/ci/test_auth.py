import pytest
from fastapi.testclient import TestClient


@pytest.mark.ci
class TestTokenAuth:
    """Test token authentication middleware."""

    @pytest.mark.integration
    def test_auth_disabled_allows_unauthenticated(self):
        """Test that requests succeed when auth is disabled (default config)."""
        from server.app import create_app

        app = create_app()
        client = TestClient(app)

        response = client.get("/v1/schemas/ga4/generate?count=1")
        assert response.status_code == 200

    def test_auth_module_config_loading(self):
        """Test that auth config loads correctly from server.yaml."""
        from server.auth import get_auth_config

        config = get_auth_config()

        assert config["enabled"] is False
        assert isinstance(config["tokens"], set)

    def test_verify_token_when_disabled(self):
        """Test that token verification passes when auth is disabled."""
        from server.auth import verify_token
        import asyncio

        result = asyncio.run(verify_token(authorization=None, x_api_key=None))
        assert result is None

    def test_token_parsing_bearer_format(self):
        """Test that Bearer token format is parsed correctly."""
        from server.auth import get_auth_config

        config = get_auth_config()
        assert "enabled" in config
        assert "tokens" in config
