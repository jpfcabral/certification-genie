"""Unit tests for question service.

Validates: Requirements 2.3, 3.5, 10.2, 15.5
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from src.api.application.services.question_service import (
    QuestionService,
    DuplicateQuestionError,
    QuestionValidationError,
    _normalize_text,
)
from src.api.domain.models.question import Question


@pytest.fixture
def mock_question_repository():
    """Create a mock QuestionRepository with AsyncMock methods."""
    repo = AsyncMock()
    repo.get_active_by_certification = AsyncMock(return_value=[])
    repo.deactivate = AsyncMock()
    repo.create = AsyncMock(side_effect=lambda item: item)
    return repo


@pytest.fixture
def mock_answer_repository():
    """Create a mock AnswerRepository with AsyncMock methods."""
    repo = AsyncMock()
    repo.get_answered_question_ids = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def question_service(mock_question_repository, mock_answer_repository):
    """Create a QuestionService instance with mocked repositories."""
    return QuestionService(
        question_repository=mock_question_repository,
        answer_repository=mock_answer_repository,
    )


@pytest.fixture
def sample_question():
    """Create a valid sample Question for testing."""
    return Question(
        id="q-test-001",
        certification="AI-103",
        domain="Generative AI and Agents",
        text="Which Azure service provides built-in orchestration for multi-turn agents?",
        options=[
            "Azure Bot Service",
            "Azure AI Agent Service",
            "Azure Cognitive Services",
            "Azure Logic Apps",
        ],
        correct_answer_index=1,
        short_explanation="Azure AI Agent Service provides orchestration.",
        detailed_explanation="Azure AI Agent Service is the correct answer because...",
        created_at=datetime.now(timezone.utc),
    )


class TestGetUnansweredQuestions:
    """Tests for get_unanswered_questions method."""

    @pytest.mark.asyncio
    async def test_returns_all_when_none_answered(
        self, question_service, mock_question_repository, mock_answer_repository
    ):
        """When user has not answered any questions, return all active ones."""
        mock_question_repository.get_active_by_certification.return_value = [
            {"id": "q-001", "text": "Q1", "certification": "AI-103"},
            {"id": "q-002", "text": "Q2", "certification": "AI-103"},
        ]
        mock_answer_repository.get_answered_question_ids.return_value = []

        result = await question_service.get_unanswered_questions("user-1", "AI-103")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_excludes_answered_questions(
        self, question_service, mock_question_repository, mock_answer_repository
    ):
        """Answered question IDs should be excluded from the result."""
        mock_question_repository.get_active_by_certification.return_value = [
            {"id": "q-001", "text": "Q1", "certification": "AI-103"},
            {"id": "q-002", "text": "Q2", "certification": "AI-103"},
            {"id": "q-003", "text": "Q3", "certification": "AI-103"},
        ]
        mock_answer_repository.get_answered_question_ids.return_value = ["q-001", "q-003"]

        result = await question_service.get_unanswered_questions("user-1", "AI-103")

        assert len(result) == 1
        assert result[0]["id"] == "q-002"

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_answered(
        self, question_service, mock_question_repository, mock_answer_repository
    ):
        """When user has answered all questions, return empty list."""
        mock_question_repository.get_active_by_certification.return_value = [
            {"id": "q-001", "text": "Q1", "certification": "AI-103"},
        ]
        mock_answer_repository.get_answered_question_ids.return_value = ["q-001"]

        result = await question_service.get_unanswered_questions("user-1", "AI-103")

        assert result == []

    @pytest.mark.asyncio
    async def test_filters_by_certification(
        self, question_service, mock_question_repository, mock_answer_repository
    ):
        """Should call repository with the correct certification filter."""
        mock_question_repository.get_active_by_certification.return_value = []
        mock_answer_repository.get_answered_question_ids.return_value = []

        await question_service.get_unanswered_questions("user-1", "AI-103")

        mock_question_repository.get_active_by_certification.assert_called_once_with(
            "AI-103"
        )


class TestValidateAndPersistQuestion:
    """Tests for validate_and_persist_question method."""

    @pytest.mark.asyncio
    async def test_persists_valid_non_duplicate_question(
        self, question_service, mock_question_repository, sample_question
    ):
        """A valid question with no duplicates should be persisted."""
        mock_question_repository.get_active_by_certification.return_value = []

        result = await question_service.validate_and_persist_question(sample_question)

        mock_question_repository.create.assert_called_once()
        assert result["id"] == "q-test-001"

    @pytest.mark.asyncio
    async def test_detects_duplicate_with_same_text(
        self, question_service, mock_question_repository, sample_question
    ):
        """Should raise DuplicateQuestionError for identical question text."""
        mock_question_repository.get_active_by_certification.return_value = [
            {
                "id": "q-existing",
                "text": sample_question.text,
                "certification": "AI-103",
            }
        ]

        with pytest.raises(DuplicateQuestionError):
            await question_service.validate_and_persist_question(sample_question)

    @pytest.mark.asyncio
    async def test_detects_duplicate_case_insensitive(
        self, question_service, mock_question_repository, sample_question
    ):
        """Duplicate detection should be case-insensitive."""
        mock_question_repository.get_active_by_certification.return_value = [
            {
                "id": "q-existing",
                "text": sample_question.text.upper(),
                "certification": "AI-103",
            }
        ]

        with pytest.raises(DuplicateQuestionError):
            await question_service.validate_and_persist_question(sample_question)

    @pytest.mark.asyncio
    async def test_detects_duplicate_with_extra_whitespace(
        self, question_service, mock_question_repository, sample_question
    ):
        """Duplicate detection should ignore extra whitespace."""
        mock_question_repository.get_active_by_certification.return_value = [
            {
                "id": "q-existing",
                "text": "  " + sample_question.text + "  ",
                "certification": "AI-103",
            }
        ]

        with pytest.raises(DuplicateQuestionError):
            await question_service.validate_and_persist_question(sample_question)

    @pytest.mark.asyncio
    async def test_allows_different_question_text(
        self, question_service, mock_question_repository, sample_question
    ):
        """Different question text should not trigger duplicate detection."""
        mock_question_repository.get_active_by_certification.return_value = [
            {
                "id": "q-existing",
                "text": "A completely different question about Azure?",
                "certification": "AI-103",
            }
        ]

        result = await question_service.validate_and_persist_question(sample_question)

        assert result is not None
        mock_question_repository.create.assert_called_once()


class TestDeactivateLowQualityQuestions:
    """Tests for deactivate_low_quality_questions method."""

    @pytest.mark.asyncio
    async def test_deactivates_questions_below_threshold(
        self, question_service, mock_question_repository
    ):
        """Questions with quality_score below threshold should be deactivated."""
        mock_question_repository.get_active_by_certification.return_value = [
            {"id": "q-001", "quality_score": 0.3, "certification": "AI-103"},
            {"id": "q-002", "quality_score": 0.8, "certification": "AI-103"},
            {"id": "q-003", "quality_score": 0.4, "certification": "AI-103"},
        ]
        mock_question_repository.deactivate.return_value = {"id": "q-001", "is_active": False}

        result = await question_service.deactivate_low_quality_questions(0.5, "AI-103")

        assert len(result) == 2
        assert mock_question_repository.deactivate.call_count == 2

    @pytest.mark.asyncio
    async def test_does_not_deactivate_above_threshold(
        self, question_service, mock_question_repository
    ):
        """Questions with quality_score at or above threshold should remain active."""
        mock_question_repository.get_active_by_certification.return_value = [
            {"id": "q-001", "quality_score": 0.7, "certification": "AI-103"},
            {"id": "q-002", "quality_score": 0.9, "certification": "AI-103"},
        ]

        result = await question_service.deactivate_low_quality_questions(0.5, "AI-103")

        assert result == []
        mock_question_repository.deactivate.assert_not_called()

    @pytest.mark.asyncio
    async def test_deactivates_at_exact_threshold(
        self, question_service, mock_question_repository
    ):
        """Questions with quality_score exactly at threshold should NOT be deactivated (< not <=)."""
        mock_question_repository.get_active_by_certification.return_value = [
            {"id": "q-001", "quality_score": 0.5, "certification": "AI-103"},
        ]

        result = await question_service.deactivate_low_quality_questions(0.5, "AI-103")

        assert result == []
        mock_question_repository.deactivate.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_missing_quality_score(
        self, question_service, mock_question_repository
    ):
        """Questions without quality_score default to 1.0 (not deactivated)."""
        mock_question_repository.get_active_by_certification.return_value = [
            {"id": "q-001", "certification": "AI-103"},
        ]

        result = await question_service.deactivate_low_quality_questions(0.5, "AI-103")

        assert result == []
        mock_question_repository.deactivate.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_active_questions(
        self, question_service, mock_question_repository
    ):
        """Should return empty list when there are no active questions."""
        mock_question_repository.get_active_by_certification.return_value = []

        result = await question_service.deactivate_low_quality_questions(0.5, "AI-103")

        assert result == []


class TestNormalizeText:
    """Tests for the _normalize_text helper function."""

    def test_lowercases_text(self):
        assert _normalize_text("Hello World") == "hello world"

    def test_strips_leading_trailing_whitespace(self):
        assert _normalize_text("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self):
        assert _normalize_text("hello   world") == "hello world"

    def test_handles_mixed_normalization(self):
        assert _normalize_text("  Hello   WORLD  ") == "hello world"
