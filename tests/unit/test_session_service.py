"""Unit tests for session service.

Validates: Requirements 4.1, 4.8, 5.1, 5.4
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from src.api.application.services.session_service import (
    SessionService,
    ActiveSessionExistsError,
    NoActiveSessionError,
)
from src.api.domain.models.session import Session


@pytest.fixture
def mock_session_repository():
    """Create a mock SessionRepository with AsyncMock methods."""
    repo = AsyncMock()
    repo.get_active_session = AsyncMock()
    repo.create_session = AsyncMock()
    repo.update_session = AsyncMock()
    return repo


@pytest.fixture
def mock_question_repository():
    """Create a mock QuestionRepository with AsyncMock methods."""
    repo = AsyncMock()
    repo.get_active_by_certification = AsyncMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_answer_repository():
    """Create a mock AnswerRepository with AsyncMock methods."""
    repo = AsyncMock()
    repo.get_answered_question_ids = AsyncMock()
    repo.get_by_user = AsyncMock()
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def session_service(
    mock_session_repository, mock_question_repository, mock_answer_repository
):
    """Create a SessionService instance with mocked repositories."""
    return SessionService(
        session_repository=mock_session_repository,
        question_repository=mock_question_repository,
        answer_repository=mock_answer_repository,
    )


class TestStartTraining:
    """Tests for start_training creating a session and serving the first question."""

    @pytest.mark.asyncio
    async def test_creates_training_session(
        self, session_service, mock_session_repository, mock_question_repository, mock_answer_repository
    ):
        """start_training should create a session with type='training'."""
        mock_session_repository.get_active_session.return_value = None
        mock_question_repository.get_active_by_certification.return_value = [
            {"id": "q-001", "domain": "Computer Vision"},
            {"id": "q-002", "domain": "Text Analysis"},
        ]
        mock_answer_repository.get_answered_question_ids.return_value = []

        result = await session_service.start_training(user_id="user-1")

        assert isinstance(result, Session)
        assert result.session_type == "training"
        assert result.is_active is True
        assert result.user_id == "user-1"

    @pytest.mark.asyncio
    async def test_serves_first_question(
        self, session_service, mock_session_repository, mock_question_repository, mock_answer_repository
    ):
        """start_training should populate questions_served with the first question."""
        mock_session_repository.get_active_session.return_value = None
        mock_question_repository.get_active_by_certification.return_value = [
            {"id": "q-001", "domain": "Computer Vision"},
            {"id": "q-002", "domain": "Text Analysis"},
        ]
        mock_answer_repository.get_answered_question_ids.return_value = []

        result = await session_service.start_training(user_id="user-1")

        assert len(result.questions_served) == 1
        assert result.questions_served[0] in ["q-001", "q-002"]
        assert result.current_question_index == 0

    @pytest.mark.asyncio
    async def test_persists_session(
        self, session_service, mock_session_repository, mock_question_repository, mock_answer_repository
    ):
        """start_training should call create_session on the repository."""
        mock_session_repository.get_active_session.return_value = None
        mock_question_repository.get_active_by_certification.return_value = [
            {"id": "q-001", "domain": "Computer Vision"},
        ]
        mock_answer_repository.get_answered_question_ids.return_value = []

        await session_service.start_training(user_id="user-1")

        mock_session_repository.create_session.assert_called_once()
        created_doc = mock_session_repository.create_session.call_args[0][0]
        assert created_doc["session_type"] == "training"
        assert created_doc["user_id"] == "user-1"
        assert created_doc["is_active"] is True

    @pytest.mark.asyncio
    async def test_raises_when_active_session_exists(
        self, session_service, mock_session_repository
    ):
        """start_training should raise ActiveSessionExistsError if session is active."""
        mock_session_repository.get_active_session.return_value = {
            "id": "existing-session",
            "user_id": "user-1",
            "session_type": "training",
            "is_active": True,
        }

        with pytest.raises(ActiveSessionExistsError):
            await session_service.start_training(user_id="user-1")


class TestStartSimulation:
    """Tests for start_simulation with default 20 questions."""

    @pytest.mark.asyncio
    async def test_creates_simulation_session(
        self, session_service, mock_session_repository, mock_question_repository, mock_answer_repository
    ):
        """start_simulation should create a session with type='simulation'."""
        mock_session_repository.get_active_session.return_value = None
        # Provide enough questions across domains
        questions = [
            {"id": f"q-{i:03d}", "domain": domain}
            for i, domain in enumerate(
                ["Generative AI and Agents"] * 10
                + ["Computer Vision"] * 5
                + ["Text Analysis"] * 5
                + ["Information Extraction"] * 5
                + ["Plan and Manage"] * 5
            )
        ]
        mock_question_repository.get_active_by_certification.return_value = questions
        mock_answer_repository.get_answered_question_ids.return_value = []

        result = await session_service.start_simulation(user_id="user-1")

        assert isinstance(result, Session)
        assert result.session_type == "simulation"
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_simulation_has_default_20_questions(
        self, session_service, mock_session_repository, mock_question_repository, mock_answer_repository
    ):
        """start_simulation with default should have total_questions=20."""
        mock_session_repository.get_active_session.return_value = None
        questions = [
            {"id": f"q-{i:03d}", "domain": domain}
            for i, domain in enumerate(
                ["Generative AI and Agents"] * 10
                + ["Computer Vision"] * 5
                + ["Text Analysis"] * 5
                + ["Information Extraction"] * 5
                + ["Plan and Manage"] * 5
            )
        ]
        mock_question_repository.get_active_by_certification.return_value = questions
        mock_answer_repository.get_answered_question_ids.return_value = []

        result = await session_service.start_simulation(user_id="user-1")

        assert result.total_questions == 20
        assert len(result.questions_served) == 20

    @pytest.mark.asyncio
    async def test_simulation_persists_session(
        self, session_service, mock_session_repository, mock_question_repository, mock_answer_repository
    ):
        """start_simulation should call create_session on the repository."""
        mock_session_repository.get_active_session.return_value = None
        questions = [
            {"id": f"q-{i:03d}", "domain": domain}
            for i, domain in enumerate(
                ["Generative AI and Agents"] * 10
                + ["Computer Vision"] * 5
                + ["Text Analysis"] * 5
                + ["Information Extraction"] * 5
                + ["Plan and Manage"] * 5
            )
        ]
        mock_question_repository.get_active_by_certification.return_value = questions
        mock_answer_repository.get_answered_question_ids.return_value = []

        await session_service.start_simulation(user_id="user-1")

        mock_session_repository.create_session.assert_called_once()
        created_doc = mock_session_repository.create_session.call_args[0][0]
        assert created_doc["session_type"] == "simulation"
        assert created_doc["total_questions"] == 20

    @pytest.mark.asyncio
    async def test_raises_when_active_session_exists(
        self, session_service, mock_session_repository
    ):
        """start_simulation should raise ActiveSessionExistsError if session is active."""
        mock_session_repository.get_active_session.return_value = {
            "id": "existing-session",
            "user_id": "user-1",
            "session_type": "simulation",
            "is_active": True,
        }

        with pytest.raises(ActiveSessionExistsError):
            await session_service.start_simulation(user_id="user-1")


class TestEndSessionExit:
    """Tests for /exit ending session and clearing state."""

    @pytest.mark.asyncio
    async def test_end_session_marks_inactive(
        self, session_service, mock_session_repository
    ):
        """end_session should set is_active=False on the session."""
        mock_session_repository.get_active_session.return_value = {
            "id": "session-1",
            "user_id": "user-1",
            "session_type": "training",
            "is_active": True,
            "started_at": "2024-01-01T00:00:00+00:00",
            "questions_served": ["q-001"],
            "current_question_index": 0,
        }

        await session_service.end_session(user_id="user-1")

        mock_session_repository.update_session.assert_called_once()
        updated_doc = mock_session_repository.update_session.call_args[0][0]
        assert updated_doc["is_active"] is False

    @pytest.mark.asyncio
    async def test_end_session_sets_ended_at(
        self, session_service, mock_session_repository
    ):
        """end_session should set ended_at timestamp."""
        mock_session_repository.get_active_session.return_value = {
            "id": "session-1",
            "user_id": "user-1",
            "session_type": "training",
            "is_active": True,
            "started_at": "2024-01-01T00:00:00+00:00",
            "questions_served": ["q-001"],
            "current_question_index": 0,
        }

        await session_service.end_session(user_id="user-1")

        updated_doc = mock_session_repository.update_session.call_args[0][0]
        assert updated_doc["ended_at"] is not None

    @pytest.mark.asyncio
    async def test_end_training_returns_none(
        self, session_service, mock_session_repository
    ):
        """end_session for training should return None (no summary)."""
        mock_session_repository.get_active_session.return_value = {
            "id": "session-1",
            "user_id": "user-1",
            "session_type": "training",
            "is_active": True,
            "started_at": "2024-01-01T00:00:00+00:00",
            "questions_served": ["q-001"],
            "current_question_index": 0,
        }

        result = await session_service.end_session(user_id="user-1")

        assert result is None

    @pytest.mark.asyncio
    async def test_end_session_raises_when_no_active_session(
        self, session_service, mock_session_repository
    ):
        """end_session should raise NoActiveSessionError if no session exists."""
        mock_session_repository.get_active_session.return_value = None

        with pytest.raises(NoActiveSessionError):
            await session_service.end_session(user_id="user-1")


class TestEndSimulation:
    """Tests for /end_simulation returning a partial summary."""

    @pytest.mark.asyncio
    async def test_end_simulation_returns_summary(
        self, session_service, mock_session_repository, mock_answer_repository, mock_question_repository
    ):
        """end_session for simulation should return a summary dict."""
        mock_session_repository.get_active_session.return_value = {
            "id": "sim-session-1",
            "user_id": "user-1",
            "session_type": "simulation",
            "is_active": True,
            "started_at": "2024-01-01T00:00:00+00:00",
            "questions_served": ["q-001", "q-002", "q-003"],
            "current_question_index": 3,
            "total_questions": 20,
        }
        # Simulate partial answers (only 3 out of 20 answered)
        mock_answer_repository.get_by_user.return_value = [
            {"question_id": "q-001", "is_correct": True, "session_id": "sim-session-1"},
            {"question_id": "q-002", "is_correct": False, "session_id": "sim-session-1"},
            {"question_id": "q-003", "is_correct": True, "session_id": "sim-session-1"},
        ]
        mock_question_repository.get_by_id.side_effect = [
            {"id": "q-001", "domain": "Computer Vision"},
            {"id": "q-002", "domain": "Text Analysis"},
            {"id": "q-003", "domain": "Computer Vision"},
        ]

        result = await session_service.end_session(user_id="user-1")

        assert result is not None
        assert "score" in result
        assert "total" in result
        assert "percentage" in result
        assert "per_domain" in result

    @pytest.mark.asyncio
    async def test_end_simulation_summary_scores_correct(
        self, session_service, mock_session_repository, mock_answer_repository, mock_question_repository
    ):
        """Summary should correctly calculate score and percentage."""
        mock_session_repository.get_active_session.return_value = {
            "id": "sim-session-1",
            "user_id": "user-1",
            "session_type": "simulation",
            "is_active": True,
            "started_at": "2024-01-01T00:00:00+00:00",
            "questions_served": ["q-001", "q-002", "q-003"],
            "current_question_index": 3,
            "total_questions": 20,
        }
        mock_answer_repository.get_by_user.return_value = [
            {"question_id": "q-001", "is_correct": True, "session_id": "sim-session-1"},
            {"question_id": "q-002", "is_correct": False, "session_id": "sim-session-1"},
            {"question_id": "q-003", "is_correct": True, "session_id": "sim-session-1"},
        ]
        mock_question_repository.get_by_id.side_effect = [
            {"id": "q-001", "domain": "Computer Vision"},
            {"id": "q-002", "domain": "Text Analysis"},
            {"id": "q-003", "domain": "Computer Vision"},
        ]

        result = await session_service.end_session(user_id="user-1")

        assert result["score"] == 2
        assert result["total"] == 3
        assert result["percentage"] == pytest.approx(66.66, rel=0.01)

    @pytest.mark.asyncio
    async def test_end_simulation_summary_per_domain(
        self, session_service, mock_session_repository, mock_answer_repository, mock_question_repository
    ):
        """Summary should include per-domain breakdown."""
        mock_session_repository.get_active_session.return_value = {
            "id": "sim-session-1",
            "user_id": "user-1",
            "session_type": "simulation",
            "is_active": True,
            "started_at": "2024-01-01T00:00:00+00:00",
            "questions_served": ["q-001", "q-002", "q-003"],
            "current_question_index": 3,
            "total_questions": 20,
        }
        mock_answer_repository.get_by_user.return_value = [
            {"question_id": "q-001", "is_correct": True, "session_id": "sim-session-1"},
            {"question_id": "q-002", "is_correct": False, "session_id": "sim-session-1"},
            {"question_id": "q-003", "is_correct": True, "session_id": "sim-session-1"},
        ]
        mock_question_repository.get_by_id.side_effect = [
            {"id": "q-001", "domain": "Computer Vision"},
            {"id": "q-002", "domain": "Text Analysis"},
            {"id": "q-003", "domain": "Computer Vision"},
        ]

        result = await session_service.end_session(user_id="user-1")

        assert "Computer Vision" in result["per_domain"]
        assert "Text Analysis" in result["per_domain"]
        assert result["per_domain"]["Computer Vision"]["correct"] == 2
        assert result["per_domain"]["Computer Vision"]["total"] == 2
        assert result["per_domain"]["Text Analysis"]["correct"] == 0
        assert result["per_domain"]["Text Analysis"]["total"] == 1

    @pytest.mark.asyncio
    async def test_end_simulation_marks_inactive(
        self, session_service, mock_session_repository, mock_answer_repository, mock_question_repository
    ):
        """end_session for simulation should still mark the session as inactive."""
        mock_session_repository.get_active_session.return_value = {
            "id": "sim-session-1",
            "user_id": "user-1",
            "session_type": "simulation",
            "is_active": True,
            "started_at": "2024-01-01T00:00:00+00:00",
            "questions_served": ["q-001"],
            "current_question_index": 1,
            "total_questions": 20,
        }
        mock_answer_repository.get_by_user.return_value = [
            {"question_id": "q-001", "is_correct": True, "session_id": "sim-session-1"},
        ]
        mock_question_repository.get_by_id.return_value = {
            "id": "q-001", "domain": "Computer Vision"
        }

        await session_service.end_session(user_id="user-1")

        updated_doc = mock_session_repository.update_session.call_args[0][0]
        assert updated_doc["is_active"] is False
        assert updated_doc["ended_at"] is not None
