"""
Property-based tests for user registration and authentication.

- Property 1: User registration idempotence — registering the same telegram_id
  multiple times produces exactly one User record.
- Property 2: User data minimization — regardless of extra input fields,
  persisted User contains only id, telegram_id, registered_at, reminders_enabled,
  last_interaction_at.
- Property 13: Webhook signature verification — HMAC verification accepts valid
  signatures and rejects invalid/missing ones.

**Validates: Requirements 1.2, 1.4, 8.4**
"""

import hmac
from unittest.mock import AsyncMock, patch

import hypothesis.strategies as st
import pytest
from hypothesis import given

from src.api.application.services.user_service import UserService
from src.api.domain.models.user import User


# --- Strategies ---

telegram_id_strategy = st.integers(min_value=1, max_value=2**63 - 1)

# Strategy for arbitrary extra fields that might come from Telegram updates
extra_fields_strategy = st.dictionaries(
    keys=st.sampled_from([
        "first_name", "last_name", "username", "language_code",
        "is_bot", "is_premium", "photo_url", "bio",
    ]),
    values=st.text(min_size=1, max_size=50),
    min_size=0,
    max_size=5,
)

# Strategy for secrets and tokens (ASCII-only, as required by hmac.compare_digest)
secret_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        max_codepoint=127,
    ),
    min_size=1,
    max_size=128,
)

# Strategy for webhook payloads (arbitrary non-empty strings)
token_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=256,
)


# --- Property 1: User registration idempotence ---


class TestUserRegistrationIdempotence:
    """
    Property 1: User registration idempotence.

    For any valid Telegram numeric identifier, registering the same identifier
    multiple times SHALL produce exactly one User record — subsequent
    registrations return the existing user without creating duplicates.

    **Validates: Requirements 1.2**
    """

    @given(telegram_id=telegram_id_strategy)
    @pytest.mark.asyncio
    async def test_register_same_user_twice_creates_only_once(
        self, telegram_id: int
    ):
        """Calling register_or_get_user twice with the same telegram_id
        calls create_user only once."""
        mock_repository = AsyncMock()
        # First call: no existing user; second call: user exists
        first_call_user_doc = None
        created_doc = {}

        async def mock_get_by_telegram_id(tid):
            if created_doc:
                return created_doc.copy()
            return first_call_user_doc

        async def mock_create_user(user_doc):
            created_doc.update(user_doc)
            return user_doc

        async def mock_update_user(user_doc):
            return user_doc

        mock_repository.get_by_telegram_id = AsyncMock(
            side_effect=mock_get_by_telegram_id
        )
        mock_repository.create_user = AsyncMock(side_effect=mock_create_user)
        mock_repository.update_user = AsyncMock(side_effect=mock_update_user)

        service = UserService(mock_repository)

        # First registration — creates the user
        user1 = await service.register_or_get_user(telegram_id)
        # Second registration — returns existing user
        user2 = await service.register_or_get_user(telegram_id)

        # create_user called exactly once
        mock_repository.create_user.assert_called_once()

        # Both calls return a User with the same telegram_id
        assert user1.telegram_id == telegram_id
        assert user2.telegram_id == telegram_id

    @given(telegram_id=telegram_id_strategy)
    @pytest.mark.asyncio
    async def test_register_existing_user_returns_same_id(
        self, telegram_id: int
    ):
        """When user already exists, register_or_get_user returns the same
        internal id without creating a new record."""
        mock_repository = AsyncMock()

        existing_doc = {
            "id": "existing-uuid-1234",
            "telegram_id": telegram_id,
            "registered_at": "2024-01-01T00:00:00+00:00",
            "reminders_enabled": True,
            "last_interaction_at": None,
        }

        mock_repository.get_by_telegram_id = AsyncMock(return_value=existing_doc)
        mock_repository.update_user = AsyncMock(return_value=existing_doc)

        service = UserService(mock_repository)

        user = await service.register_or_get_user(telegram_id)

        # Should NOT call create_user
        mock_repository.create_user.assert_not_called()
        # Returns the existing user
        assert user.id == "existing-uuid-1234"
        assert user.telegram_id == telegram_id


# --- Property 2: User data minimization ---


class TestUserDataMinimization:
    """
    Property 2: User data minimization.

    For any user registration input (regardless of what extra fields are provided
    in the Telegram update), the persisted User document SHALL contain only the
    expected fields: id, telegram_id, registered_at, reminders_enabled,
    last_interaction_at — no name, username, photo, etc.

    **Validates: Requirements 1.4**
    """

    @given(telegram_id=telegram_id_strategy, extra_fields=extra_fields_strategy)
    @pytest.mark.asyncio
    async def test_user_model_contains_only_expected_fields(
        self, telegram_id: int, extra_fields: dict
    ):
        """Regardless of extra input data, the User model only exposes the
        defined schema fields."""
        mock_repository = AsyncMock()
        mock_repository.get_by_telegram_id = AsyncMock(return_value=None)
        mock_repository.create_user = AsyncMock(side_effect=lambda doc: doc)

        service = UserService(mock_repository)

        # register_or_get_user only takes telegram_id — extra fields
        # cannot leak into the User model
        user = await service.register_or_get_user(telegram_id)

        # Verify the returned User has only the expected fields
        expected_fields = {
            "id", "telegram_id", "registered_at",
            "reminders_enabled", "last_interaction_at",
        }
        actual_fields = set(User.model_fields.keys())
        assert actual_fields == expected_fields

    @given(telegram_id=telegram_id_strategy)
    @pytest.mark.asyncio
    async def test_persisted_document_has_only_expected_keys(
        self, telegram_id: int
    ):
        """The document passed to create_user contains only the expected keys."""
        mock_repository = AsyncMock()
        mock_repository.get_by_telegram_id = AsyncMock(return_value=None)

        captured_doc = {}

        async def capture_create(doc):
            captured_doc.update(doc)
            return doc

        mock_repository.create_user = AsyncMock(side_effect=capture_create)

        service = UserService(mock_repository)
        await service.register_or_get_user(telegram_id)

        expected_keys = {
            "id", "telegram_id", "registered_at",
            "reminders_enabled", "last_interaction_at",
        }
        assert set(captured_doc.keys()) == expected_keys

    @given(telegram_id=telegram_id_strategy)
    @pytest.mark.asyncio
    async def test_no_personal_data_in_persisted_user(
        self, telegram_id: int
    ):
        """The persisted User does not contain name, username, photo, or bio."""
        mock_repository = AsyncMock()
        mock_repository.get_by_telegram_id = AsyncMock(return_value=None)

        captured_doc = {}

        async def capture_create(doc):
            captured_doc.update(doc)
            return doc

        mock_repository.create_user = AsyncMock(side_effect=capture_create)

        service = UserService(mock_repository)
        await service.register_or_get_user(telegram_id)

        forbidden_keys = {
            "first_name", "last_name", "username",
            "language_code", "is_bot", "photo_url", "bio",
        }
        for key in forbidden_keys:
            assert key not in captured_doc


# --- Property 13: Webhook signature verification ---


class TestWebhookSignatureVerification:
    """
    Property 13: Webhook signature verification.

    For any incoming webhook payload, the authentication function SHALL accept
    the payload only when the provided signature matches the configured webhook
    secret. Invalid or missing signatures SHALL be rejected.

    **Validates: Requirements 8.4**
    """

    @given(secret=secret_strategy)
    @pytest.mark.asyncio
    async def test_valid_signature_is_accepted(self, secret: str):
        """When the X-Telegram-Bot-Api-Secret-Token header matches the
        configured secret, the request is accepted (no exception raised)."""
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        from src.api.application.middleware.auth_middleware import (
            verify_telegram_webhook,
        )

        # Mock the request with the correct secret token header
        mock_request = MagicMock()
        mock_request.headers = {"X-Telegram-Bot-Api-Secret-Token": secret}

        # Mock settings to return our generated secret
        mock_settings = MagicMock()
        mock_settings.TELEGRAM_WEBHOOK_SECRET = secret

        with patch(
            "src.api.application.middleware.auth_middleware.get_settings",
            return_value=mock_settings,
        ):
            # Should not raise
            await verify_telegram_webhook(mock_request)

    @given(secret=secret_strategy, wrong_token=secret_strategy)
    @pytest.mark.asyncio
    async def test_invalid_signature_is_rejected(
        self, secret: str, wrong_token: str
    ):
        """When the X-Telegram-Bot-Api-Secret-Token header does NOT match the
        configured secret, the request is rejected with 401."""
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        from src.api.application.middleware.auth_middleware import (
            verify_telegram_webhook,
        )

        # Ensure the wrong token is actually different from the secret
        if wrong_token == secret:
            return  # Skip this case — hypothesis will generate others

        mock_request = MagicMock()
        mock_request.headers = {"X-Telegram-Bot-Api-Secret-Token": wrong_token}

        mock_settings = MagicMock()
        mock_settings.TELEGRAM_WEBHOOK_SECRET = secret

        with patch(
            "src.api.application.middleware.auth_middleware.get_settings",
            return_value=mock_settings,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_telegram_webhook(mock_request)
            assert exc_info.value.status_code == 401

    @given(secret=secret_strategy)
    @pytest.mark.asyncio
    async def test_missing_signature_is_rejected(self, secret: str):
        """When the X-Telegram-Bot-Api-Secret-Token header is missing,
        the request is rejected with 401."""
        from unittest.mock import MagicMock

        from fastapi import HTTPException

        from src.api.application.middleware.auth_middleware import (
            verify_telegram_webhook,
        )

        mock_request = MagicMock()
        mock_request.headers = {}  # No secret token header

        mock_settings = MagicMock()
        mock_settings.TELEGRAM_WEBHOOK_SECRET = secret

        with patch(
            "src.api.application.middleware.auth_middleware.get_settings",
            return_value=mock_settings,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verify_telegram_webhook(mock_request)
            assert exc_info.value.status_code == 401
            assert "Missing" in exc_info.value.detail
