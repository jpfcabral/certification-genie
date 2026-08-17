"""Unit tests for Telegram webhook authentication middleware.

Validates: Requirements 8.4, 8.5
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException

from src.api.application.middleware.auth_middleware import verify_telegram_webhook


def _make_request(headers: dict) -> MagicMock:
    """Create a mock Request object with the given headers."""
    request = MagicMock()
    request.headers = headers
    return request


class TestVerifyTelegramWebhook:
    """Tests for verify_telegram_webhook dependency."""

    @pytest.mark.asyncio
    @patch("src.api.application.middleware.auth_middleware.get_settings")
    async def test_valid_signature_passes(self, mock_get_settings):
        """Request with correct secret token should pass without error."""
        mock_settings = MagicMock()
        mock_settings.TELEGRAM_WEBHOOK_SECRET = "my-secret-token"
        mock_get_settings.return_value = mock_settings

        request = _make_request(
            {"X-Telegram-Bot-Api-Secret-Token": "my-secret-token"}
        )

        # Should not raise
        await verify_telegram_webhook(request)

    @pytest.mark.asyncio
    @patch("src.api.application.middleware.auth_middleware.get_settings")
    async def test_missing_header_returns_401(self, mock_get_settings):
        """Request without the secret token header should raise 401."""
        mock_settings = MagicMock()
        mock_settings.TELEGRAM_WEBHOOK_SECRET = "my-secret-token"
        mock_get_settings.return_value = mock_settings

        request = _make_request({})

        with pytest.raises(HTTPException) as exc_info:
            await verify_telegram_webhook(request)

        assert exc_info.value.status_code == 401
        assert "Missing" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.api.application.middleware.auth_middleware.get_settings")
    async def test_invalid_signature_returns_401(self, mock_get_settings):
        """Request with wrong secret token should raise 401."""
        mock_settings = MagicMock()
        mock_settings.TELEGRAM_WEBHOOK_SECRET = "my-secret-token"
        mock_get_settings.return_value = mock_settings

        request = _make_request(
            {"X-Telegram-Bot-Api-Secret-Token": "wrong-token"}
        )

        with pytest.raises(HTTPException) as exc_info:
            await verify_telegram_webhook(request)

        assert exc_info.value.status_code == 401
        assert "Invalid" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.api.application.middleware.auth_middleware.get_settings")
    async def test_empty_string_token_returns_401(self, mock_get_settings):
        """Request with empty string as token should raise 401."""
        mock_settings = MagicMock()
        mock_settings.TELEGRAM_WEBHOOK_SECRET = "my-secret-token"
        mock_get_settings.return_value = mock_settings

        request = _make_request(
            {"X-Telegram-Bot-Api-Secret-Token": ""}
        )

        with pytest.raises(HTTPException) as exc_info:
            await verify_telegram_webhook(request)

        assert exc_info.value.status_code == 401
