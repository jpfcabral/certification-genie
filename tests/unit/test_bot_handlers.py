"""Unit tests for bot handlers.

Tests command handlers, poll answer handler, and callback handler
using pytest + AsyncMock. Services are mocked via context.bot_data.

Validates: Requirements 1.1, 1.3, 4.1, 4.8, 15.3
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.domain.models.session import Session
from src.api.domain.models.user import User
from src.api.application.services.session_service import NoActiveSessionError


# ---- Fixtures ----


@pytest.fixture
def mock_user():
    """A minimal User model for tests."""
    return User(
        id="user-uuid-1",
        telegram_id=123456789,
        registered_at="2024-01-01T00:00:00+00:00",
    )


@pytest.fixture
def mock_user_service(mock_user):
    """Mock UserService with register_or_get_user returning mock_user."""
    service = AsyncMock()
    service.register_or_get_user = AsyncMock(return_value=mock_user)
    return service


@pytest.fixture
def mock_session_service():
    """Mock SessionService."""
    service = AsyncMock()
    service.start_training = AsyncMock()
    service.start_simulation = AsyncMock()
    service.start_free_qa = AsyncMock()
    service.end_session = AsyncMock()
    service.get_current_session = AsyncMock()
    service.record_answer = AsyncMock()
    return service


@pytest.fixture
def mock_question_service():
    """Mock QuestionService with a nested question repository."""
    service = AsyncMock()
    service._question_repository = AsyncMock()
    service._question_repository.get_by_id = AsyncMock()
    return service


@pytest.fixture
def mock_feedback_service():
    """Mock FeedbackService."""
    service = AsyncMock()
    service.record_feedback = AsyncMock()
    return service


@pytest.fixture
def mock_progress_service():
    """Mock ProgressService."""
    service = AsyncMock()
    service.calculate_progress = AsyncMock()
    service.get_weak_areas = AsyncMock()
    return service


@pytest.fixture
def context(
    mock_user_service,
    mock_session_service,
    mock_question_service,
    mock_feedback_service,
    mock_progress_service,
):
    """Mock telegram.ext context with services in bot_data."""
    ctx = MagicMock()
    ctx.bot_data = {
        "user_service": mock_user_service,
        "session_service": mock_session_service,
        "question_service": mock_question_service,
        "feedback_service": mock_feedback_service,
        "progress_service": mock_progress_service,
        "poll_to_question": {},
        "poll_to_user": {},
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
    upd.message.reply_poll = AsyncMock()
    return upd


# ---- /start handler tests ----


class TestStartHandler:
    """Test /start with new user triggers registration and shows main menu."""

    @pytest.mark.asyncio
    async def test_registers_user_on_start(self, update, context, mock_user_service):
        """handle_start should call register_or_get_user with the telegram id."""
        from src.bot.handlers.command_handler import handle_start

        await handle_start(update, context)

        mock_user_service.register_or_get_user.assert_called_once_with(123456789)

    @pytest.mark.asyncio
    async def test_shows_main_menu(self, update, context):
        """handle_start should reply with the main menu keyboard."""
        from src.bot.handlers.command_handler import handle_start

        await handle_start(update, context)

        update.message.reply_text.assert_called_once()
        call_kwargs = update.message.reply_text.call_args
        # Check that reply_markup is present (main menu keyboard)
        assert call_kwargs.kwargs.get("reply_markup") is not None or (
            len(call_kwargs.args) >= 1 and "reply_markup" in (call_kwargs.kwargs or {})
        )

    @pytest.mark.asyncio
    async def test_welcome_message_text(self, update, context):
        """handle_start should include a welcome message."""
        from src.bot.handlers.command_handler import handle_start

        await handle_start(update, context)

        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args.kwargs.get("text", "")
        assert "Welcome" in message_text or "welcome" in message_text.lower()


# ---- /train handler tests ----


class TestTrainHandler:
    """Test /train starts training session."""

    @pytest.mark.asyncio
    async def test_starts_training_session(
        self, update, context, mock_user, mock_session_service
    ):
        """handle_train should call start_training with the user's id."""
        from src.bot.handlers.command_handler import handle_train

        mock_session_service.start_training.return_value = Session(
            id="session-1",
            user_id=mock_user.id,
            session_type="training",
            started_at="2024-01-01T00:00:00+00:00",
            questions_served=["q-001"],
            current_question_index=0,
            is_active=True,
        )
        mock_question_service = context.bot_data["question_service"]
        mock_question_service._question_repository.get_by_id.return_value = {
            "id": "q-001",
            "certification": "AI-103",
            "domain": "Computer Vision",
            "text": "What is Azure CV?",
            "options": ["A", "B", "C", "D"],
            "correct_answer_index": 1,
            "short_explanation": "Because B.",
            "detailed_explanation": "Detailed B.",
            "created_at": "2024-01-01T00:00:00+00:00",
        }

        # Make reply_poll return a mock message with poll.id
        sent_message = MagicMock()
        sent_message.poll = MagicMock()
        sent_message.poll.id = "poll-123"
        update.message.reply_poll.return_value = sent_message

        await handle_train(update, context)

        mock_session_service.start_training.assert_called_once_with(mock_user.id)

    @pytest.mark.asyncio
    async def test_sends_first_question_as_poll(
        self, update, context, mock_user, mock_session_service
    ):
        """handle_train should send the first question as a poll."""
        from src.bot.handlers.command_handler import handle_train

        mock_session_service.start_training.return_value = Session(
            id="session-1",
            user_id=mock_user.id,
            session_type="training",
            started_at="2024-01-01T00:00:00+00:00",
            questions_served=["q-001"],
            current_question_index=0,
            is_active=True,
        )
        mock_question_service = context.bot_data["question_service"]
        mock_question_service._question_repository.get_by_id.return_value = {
            "id": "q-001",
            "certification": "AI-103",
            "domain": "Computer Vision",
            "text": "What is Azure CV?",
            "options": ["A", "B", "C", "D"],
            "correct_answer_index": 1,
            "short_explanation": "Because B.",
            "detailed_explanation": "Detailed B.",
            "created_at": "2024-01-01T00:00:00+00:00",
        }

        sent_message = MagicMock()
        sent_message.poll = MagicMock()
        sent_message.poll.id = "poll-123"
        update.message.reply_poll.return_value = sent_message

        await handle_train(update, context)

        update.message.reply_poll.assert_called_once()
        call_kwargs = update.message.reply_poll.call_args.kwargs
        assert call_kwargs["type"] == "quiz"
        assert call_kwargs["is_anonymous"] is False
        assert len(call_kwargs["options"]) == 4

    @pytest.mark.asyncio
    async def test_no_questions_available(
        self, update, context, mock_user, mock_session_service
    ):
        """handle_train should inform user when no questions are available."""
        from src.bot.handlers.command_handler import handle_train

        mock_session_service.start_training.return_value = Session(
            id="session-1",
            user_id=mock_user.id,
            session_type="training",
            started_at="2024-01-01T00:00:00+00:00",
            questions_served=[],
            current_question_index=0,
            is_active=True,
        )

        await handle_train(update, context)

        update.message.reply_text.assert_called_once()
        msg = update.message.reply_text.call_args[0][0]
        assert "no questions" in msg.lower() or "No questions" in msg


# ---- /exit handler tests ----


class TestExitHandler:
    """Test /exit ends current session."""

    @pytest.mark.asyncio
    async def test_ends_active_session(
        self, update, context, mock_user, mock_session_service
    ):
        """handle_exit should call end_session with the user's id."""
        from src.bot.handlers.command_handler import handle_exit

        mock_session_service.end_session.return_value = None

        await handle_exit(update, context)

        mock_session_service.end_session.assert_called_once_with(mock_user.id)

    @pytest.mark.asyncio
    async def test_shows_main_menu_after_exit(
        self, update, context, mock_session_service
    ):
        """handle_exit should display main menu after ending a non-simulation session."""
        from src.bot.handlers.command_handler import handle_exit

        mock_session_service.end_session.return_value = None

        await handle_exit(update, context)

        update.message.reply_text.assert_called_once()
        call_kwargs = update.message.reply_text.call_args
        assert call_kwargs.kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_handles_no_active_session(
        self, update, context, mock_session_service
    ):
        """handle_exit should inform user when no active session exists."""
        from src.bot.handlers.command_handler import handle_exit

        mock_session_service.end_session.side_effect = NoActiveSessionError(
            "No active session"
        )

        await handle_exit(update, context)

        update.message.reply_text.assert_called_once()
        msg = update.message.reply_text.call_args[0][0]
        assert "no active session" in msg.lower() or "No active session" in msg


# ---- Poll answer routing tests ----


class TestPollAnswerHandler:
    """Test poll answer routing to session service."""

    @pytest.mark.asyncio
    async def test_routes_poll_answer_to_session_service(self, context, mock_session_service):
        """handle_poll_answer should record the answer via session service."""
        from src.bot.handlers.poll_handler import handle_poll_answer

        # Set up poll-to-question mapping
        context.bot_data["poll_to_question"] = {"poll-abc": "q-001"}
        context.bot_data["poll_to_user"] = {"poll-abc": "user-uuid-1"}

        # Mock poll_answer
        poll_update = MagicMock()
        poll_update.poll_answer = MagicMock()
        poll_update.poll_answer.poll_id = "poll-abc"
        poll_update.poll_answer.option_ids = [2]
        poll_update.poll_answer.user = MagicMock()
        poll_update.poll_answer.user.id = 123456789

        # Mock session service
        answer_record = MagicMock()
        answer_record.is_correct = True
        mock_session_service.record_answer.return_value = answer_record

        # Mock current session for follow-up
        mock_session_service.get_current_session.return_value = Session(
            id="session-1",
            user_id="user-uuid-1",
            session_type="training",
            started_at="2024-01-01T00:00:00+00:00",
            questions_served=["q-001"],
            current_question_index=1,
            is_active=True,
        )

        # Mock question repo for training follow-up
        mock_question_service = context.bot_data["question_service"]
        mock_question_service._question_repository.get_by_id.return_value = None

        await handle_poll_answer(poll_update, context)

        mock_session_service.record_answer.assert_called_once_with(
            user_id="user-uuid-1",
            question_id="q-001",
            selected_answer=2,
        )

    @pytest.mark.asyncio
    async def test_ignores_unknown_poll(self, context, mock_session_service):
        """handle_poll_answer should skip polls not in the mapping."""
        from src.bot.handlers.poll_handler import handle_poll_answer

        context.bot_data["poll_to_question"] = {}
        context.bot_data["poll_to_user"] = {}

        poll_update = MagicMock()
        poll_update.poll_answer = MagicMock()
        poll_update.poll_answer.poll_id = "unknown-poll"
        poll_update.poll_answer.option_ids = [0]
        poll_update.poll_answer.user = MagicMock()
        poll_update.poll_answer.user.id = 123456789

        await handle_poll_answer(poll_update, context)

        mock_session_service.record_answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_no_poll_answer(self, context):
        """handle_poll_answer should return early if poll_answer is None."""
        from src.bot.handlers.poll_handler import handle_poll_answer

        poll_update = MagicMock()
        poll_update.poll_answer = None

        # Should not raise
        await handle_poll_answer(poll_update, context)


# ---- Feedback callback tests ----


class TestFeedbackCallbacks:
    """Test feedback button callbacks."""

    @pytest.fixture
    def callback_update(self):
        """Mock update with a callback_query for feedback tests."""
        upd = MagicMock()
        upd.callback_query = AsyncMock()
        upd.callback_query.answer = AsyncMock()
        upd.callback_query.data = "feedback:positive:q-001"
        upd.callback_query.edit_message_text = AsyncMock()
        upd.callback_query.edit_message_reply_markup = AsyncMock()
        upd.effective_user = MagicMock()
        upd.effective_user.id = 123456789
        return upd

    @pytest.mark.asyncio
    async def test_positive_feedback_records(
        self, callback_update, context, mock_feedback_service, mock_user
    ):
        """Positive feedback callback should record positive rating."""
        from src.bot.handlers.callback_handler import handle_callback_query

        callback_update.callback_query.data = "feedback:positive:q-001"

        await handle_callback_query(callback_update, context)

        mock_feedback_service.record_feedback.assert_called_once_with(
            user_id=mock_user.id,
            question_id="q-001",
            rating="positive",
        )

    @pytest.mark.asyncio
    async def test_negative_feedback_records(
        self, callback_update, context, mock_feedback_service, mock_user
    ):
        """Negative feedback callback should record negative rating."""
        from src.bot.handlers.callback_handler import handle_callback_query

        callback_update.callback_query.data = "feedback:negative:q-002"

        await handle_callback_query(callback_update, context)

        mock_feedback_service.record_feedback.assert_called_once_with(
            user_id=mock_user.id,
            question_id="q-002",
            rating="negative",
        )

    @pytest.mark.asyncio
    async def test_flag_shows_subcategories(self, callback_update, context):
        """Flag feedback callback should show flag subcategory keyboard."""
        from src.bot.handlers.callback_handler import handle_callback_query

        callback_update.callback_query.data = "feedback:flag:q-001"

        await handle_callback_query(callback_update, context)

        callback_update.callback_query.edit_message_reply_markup.assert_called_once()

    @pytest.mark.asyncio
    async def test_flag_subcategory_records_with_flag_type(
        self, callback_update, context, mock_feedback_service, mock_user
    ):
        """Selecting a flag subcategory should record feedback with flag_type."""
        from src.bot.handlers.callback_handler import handle_callback_query

        callback_update.callback_query.data = "flag:incorrect_answer:q-003"

        await handle_callback_query(callback_update, context)

        mock_feedback_service.record_feedback.assert_called_once_with(
            user_id=mock_user.id,
            question_id="q-003",
            rating="negative",
            flag_type="incorrect_answer",
        )

    @pytest.mark.asyncio
    async def test_callback_answers_query(self, callback_update, context):
        """All callbacks should acknowledge the query with answer()."""
        from src.bot.handlers.callback_handler import handle_callback_query

        callback_update.callback_query.data = "feedback:positive:q-001"

        await handle_callback_query(callback_update, context)

        callback_update.callback_query.answer.assert_called_once()
