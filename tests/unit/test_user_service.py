"""Unit tests for user service with idempotent registration.

Validates: Requirements 1.1, 1.2, 8.4
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from src.api.application.services.user_service import UserService
from src.api.domain.models.user import User


@pytest.fixture
def mock_user_repository():
    """Create a mock UserRepository with AsyncMock methods."""
    repo = AsyncMock()
    repo.get_by_telegram_id = AsyncMock()
    repo.create_user = AsyncMock()
    repo.update_user = AsyncMock()
    return repo


@pytest.fixture
def user_service(mock_user_repository):
    """Create a UserService instance with a mocked repository."""
    return UserService(user_repository=mock_user_repository)


class TestRegisterOrGetUserNewUser:
    """Tests for registering a new user via register_or_get_user."""

    @pytest.mark.asyncio
    async def test_new_user_calls_create_user(self, user_service, mock_user_repository):
        """When telegram_id does not exist, create_user should be called."""
        mock_user_repository.get_by_telegram_id.return_value = None

        await user_service.register_or_get_user(telegram_id=123456789)

        mock_user_repository.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_user_returns_user_model(self, user_service, mock_user_repository):
        """When telegram_id is new, should return a User model instance."""
        mock_user_repository.get_by_telegram_id.return_value = None

        result = await user_service.register_or_get_user(telegram_id=123456789)

        assert isinstance(result, User)
        assert result.telegram_id == 123456789

    @pytest.mark.asyncio
    async def test_new_user_has_correct_fields(self, user_service, mock_user_repository):
        """New user should have id, telegram_id, and registered_at set."""
        mock_user_repository.get_by_telegram_id.return_value = None

        result = await user_service.register_or_get_user(telegram_id=987654321)

        assert result.id is not None
        assert len(result.id) > 0  # UUID string
        assert result.telegram_id == 987654321
        assert result.registered_at is not None

    @pytest.mark.asyncio
    async def test_new_user_create_called_with_correct_data(
        self, user_service, mock_user_repository
    ):
        """create_user should be called with a dict containing the user data."""
        mock_user_repository.get_by_telegram_id.return_value = None

        await user_service.register_or_get_user(telegram_id=111222333)

        call_args = mock_user_repository.create_user.call_args[0][0]
        assert call_args["telegram_id"] == 111222333
        assert "id" in call_args
        assert "registered_at" in call_args


class TestRegisterOrGetUserExistingUser:
    """Tests for returning an existing user via register_or_get_user."""

    @pytest.mark.asyncio
    async def test_existing_user_does_not_call_create(
        self, user_service, mock_user_repository
    ):
        """When telegram_id already exists, create_user should NOT be called."""
        mock_user_repository.get_by_telegram_id.return_value = {
            "id": "existing-uuid",
            "telegram_id": 123456789,
            "registered_at": "2024-01-01T00:00:00+00:00",
            "reminders_enabled": True,
            "last_interaction_at": None,
        }

        await user_service.register_or_get_user(telegram_id=123456789)

        mock_user_repository.create_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_existing_user_returns_same_record(
        self, user_service, mock_user_repository
    ):
        """When telegram_id exists, should return the existing user data."""
        mock_user_repository.get_by_telegram_id.return_value = {
            "id": "existing-uuid",
            "telegram_id": 123456789,
            "registered_at": "2024-01-01T00:00:00+00:00",
            "reminders_enabled": True,
            "last_interaction_at": None,
        }

        result = await user_service.register_or_get_user(telegram_id=123456789)

        assert isinstance(result, User)
        assert result.id == "existing-uuid"
        assert result.telegram_id == 123456789

    @pytest.mark.asyncio
    async def test_existing_user_updates_last_interaction(
        self, user_service, mock_user_repository
    ):
        """When existing user is found, last_interaction_at should be updated."""
        mock_user_repository.get_by_telegram_id.return_value = {
            "id": "existing-uuid",
            "telegram_id": 123456789,
            "registered_at": "2024-01-01T00:00:00+00:00",
            "reminders_enabled": True,
            "last_interaction_at": None,
        }

        await user_service.register_or_get_user(telegram_id=123456789)

        mock_user_repository.update_user.assert_called_once()
        updated_doc = mock_user_repository.update_user.call_args[0][0]
        assert updated_doc["last_interaction_at"] is not None
