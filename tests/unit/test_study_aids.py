"""Unit tests for study aid features: /flashcard, /domains, /weak_areas, /reminders.

Uses pytest + AsyncMock, same pattern as test_bot_handlers.py.
Services are mocked via context.bot_data.

Validates: Requirements 17.1, 17.2, 17.3, 17.5
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.api.domain.models.user import User


# ---- Fixtures ----


@pytest.fixture
def mock_user():
    """A minimal User model for tests."""
    return User(
        id="user-uuid-1",
        telegram_id=123456789,
        registered_at="2024-01-01T00:00:00+00:00",
        reminders_enabled=True,
    )


@pytest.fixture
def mock_user_service(mock_user):
    """Mock UserService with register_or_get_user returning mock_user."""
    service = AsyncMock()
    service.register_or_get_user = AsyncMock(return_value=mock_user)
    service._repository = AsyncMock()
    service._repository.get_by_telegram_id = AsyncMock()
    service._repository.update_user = AsyncMock()
    return service


@pytest.fixture
def mock_progress_service():
    """Mock ProgressService."""
    service = AsyncMock()
    service.calculate_progress = AsyncMock()
    service.get_weak_areas = AsyncMock()
    return service


@pytest.fixture
def context(mock_user_service, mock_progress_service):
    """Mock telegram.ext context with services in bot_data."""
    ctx = MagicMock()
    ctx.bot_data = {
        "user_service": mock_user_service,
        "progress_service": mock_progress_service,
    }
    ctx.bot = AsyncMock()
    ctx.args = []
    return ctx


@pytest.fixture
def update():
    """Mock telegram Update with effective_user and message."""
    upd = MagicMock()
    upd.effective_user = MagicMock()
    upd.effective_user.id = 123456789
    upd.message = AsyncMock()
    upd.message.reply_text = AsyncMock()
    return upd


# ---- /flashcard handler tests ----


class TestFlashcardHandler:
    """Test /flashcard returns a valid domain concept."""

    @pytest.mark.asyncio
    async def test_flashcard_sends_message_with_domain_name(self, update, context):
        """handle_flashcard should send a message containing a valid domain name."""
        from src.bot.handlers.command_handler import handle_flashcard
        from src.api.domain.enums.domain_type import DomainType

        await handle_flashcard(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")

        # The message should contain one of the valid domain names
        valid_domains = [d.value for d in DomainType]
        assert any(
            domain in message_text for domain in valid_domains
        ), f"Message '{message_text}' does not contain any valid domain name"

    @pytest.mark.asyncio
    async def test_flashcard_includes_reveal_button(self, update, context):
        """handle_flashcard should include an InlineKeyboard with a reveal button."""
        from src.bot.handlers.command_handler import handle_flashcard

        await handle_flashcard(update, context)

        call_kwargs = update.message.reply_text.call_args.kwargs
        assert call_kwargs.get("reply_markup") is not None


# ---- /domains handler tests ----


class TestDomainsHandler:
    """Test /domains shows all domains with correct weights."""

    @pytest.mark.asyncio
    async def test_domains_shows_all_five_domains(
        self, update, context, mock_progress_service
    ):
        """handle_domains should include all 5 domain names in the message."""
        from src.bot.handlers.command_handler import handle_domains
        from src.api.domain.enums.domain_type import DomainType

        mock_progress_service.calculate_progress.return_value = {
            "total_answered": 10,
            "overall_percentage": 70.0,
            "per_domain": {},
        }

        await handle_domains(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")

        # All 5 domain names must be present
        for domain in DomainType:
            assert domain.value in message_text, (
                f"Domain '{domain.value}' not found in /domains message"
            )

    @pytest.mark.asyncio
    async def test_domains_shows_weight_percentages(
        self, update, context, mock_progress_service
    ):
        """handle_domains should display weight percentages for each domain."""
        from src.bot.handlers.command_handler import handle_domains

        mock_progress_service.calculate_progress.return_value = {
            "total_answered": 10,
            "overall_percentage": 70.0,
            "per_domain": {},
        }

        await handle_domains(update, context)

        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")

        # Weights: 35%, 15%, 20%, 15%, 15% - at least these should appear
        assert "35%" in message_text
        assert "20%" in message_text
        assert "15%" in message_text


# ---- /weak_areas handler tests ----


class TestWeakAreasHandler:
    """Test /weak_areas with sufficient data returns 3 domains."""

    @pytest.mark.asyncio
    async def test_weak_areas_returns_three_domains(
        self, update, context, mock_progress_service
    ):
        """handle_weak_areas with sufficient data should display 3 weak domains."""
        from src.bot.handlers.command_handler import handle_weak_areas

        mock_progress_service.get_weak_areas.return_value = [
            {"domain": "Computer Vision", "percentage": 40.0},
            {"domain": "Text Analysis", "percentage": 50.0},
            {"domain": "Information Extraction", "percentage": 55.0},
        ]

        await handle_weak_areas(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")

        assert "Computer Vision" in message_text
        assert "Text Analysis" in message_text
        assert "Information Extraction" in message_text

    @pytest.mark.asyncio
    async def test_weak_areas_insufficient_data(
        self, update, context, mock_progress_service
    ):
        """handle_weak_areas with insufficient data should show limited info."""
        from src.bot.handlers.command_handler import handle_weak_areas

        mock_progress_service.get_weak_areas.return_value = {
            "insufficient_data": True,
            "total_answered": 3,
        }

        await handle_weak_areas(update, context)

        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")

        assert "3" in message_text


# ---- /reminders handler tests ----


class TestRemindersHandler:
    """Test reminder toggle on/off."""

    @pytest.mark.asyncio
    async def test_reminders_on(self, update, context, mock_user_service):
        """handle_reminders with args=["on"] should enable reminders."""
        from src.bot.handlers.command_handler import handle_reminders

        context.args = ["on"]

        # Mock the repository calls used in handle_reminders
        mock_user_service._repository.get_by_telegram_id.return_value = {
            "id": "user-uuid-1",
            "telegram_id": 123456789,
            "registered_at": "2024-01-01T00:00:00+00:00",
            "reminders_enabled": False,
        }

        await handle_reminders(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")

        assert "enabled" in message_text

    @pytest.mark.asyncio
    async def test_reminders_off(self, update, context, mock_user_service):
        """handle_reminders with args=["off"] should disable reminders."""
        from src.bot.handlers.command_handler import handle_reminders

        context.args = ["off"]

        mock_user_service._repository.get_by_telegram_id.return_value = {
            "id": "user-uuid-1",
            "telegram_id": 123456789,
            "registered_at": "2024-01-01T00:00:00+00:00",
            "reminders_enabled": True,
        }

        await handle_reminders(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")

        assert "disabled" in message_text

    @pytest.mark.asyncio
    async def test_reminders_no_args_shows_status(self, update, context):
        """handle_reminders with no args should show current status."""
        from src.bot.handlers.command_handler import handle_reminders

        context.args = []

        await handle_reminders(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")

        assert "enabled" in message_text or "disabled" in message_text
