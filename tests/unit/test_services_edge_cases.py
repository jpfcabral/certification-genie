"""Edge case unit tests for services.

Complements test_question_service.py and test_progress_service.py
with focused boundary condition tests.

Validates: Requirements 11.3, 15.5, 3.5
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from src.api.application.services.progress_service import ProgressService
from src.api.application.services.question_service import (
    DuplicateQuestionError,
    QuestionService,
)
from src.api.domain.models.question import Question


# --- Fixtures ---


@pytest.fixture
def mock_answer_repository():
    repo = AsyncMock()
    repo.get_by_user = AsyncMock()
    repo.get_answered_question_ids = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_question_repository():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_active_by_certification = AsyncMock(return_value=[])
    repo.deactivate = AsyncMock()
    repo.create = AsyncMock(side_effect=lambda item: item)
    return repo


@pytest.fixture
def progress_service(mock_answer_repository, mock_question_repository):
    return ProgressService(
        answer_repository=mock_answer_repository,
        question_repository=mock_question_repository,
    )


@pytest.fixture
def question_service(mock_question_repository, mock_answer_repository):
    return QuestionService(
        question_repository=mock_question_repository,
        answer_repository=mock_answer_repository,
    )


def _make_answer(question_id: str, is_correct: bool) -> dict:
    return {
        "id": f"ans-{question_id}",
        "user_id": "user-1",
        "question_id": question_id,
        "selected_answer": 1 if is_correct else 2,
        "is_correct": is_correct,
        "context": "training",
        "session_id": "sess-1",
        "answered_at": "2024-12-01T10:00:00Z",
    }


def _make_question(question_id: str, domain: str) -> dict:
    return {
        "id": question_id,
        "certification": "AI-103",
        "domain": domain,
        "text": f"Question {question_id}",
        "options": ["A", "B", "C", "D"],
        "correct_answer_index": 1,
        "short_explanation": "Explanation",
        "detailed_explanation": "Detailed explanation",
        "created_at": "2024-12-01T00:00:00Z",
        "quality_score": 1.0,
        "is_active": True,
    }


# --- Progress Edge Cases ---


class TestProgressBoundaryAtFiveAnswers:
    """Tests for the exact boundary at 5 answers (minimum for analysis)."""

    @pytest.mark.asyncio
    async def test_exactly_five_answers_returns_full_progress(
        self, progress_service, mock_answer_repository, mock_question_repository
    ):
        """With exactly 5 answers, should return full progress (no insufficient_data).

        This verifies the boundary: 4 answers → insufficient_data, 5 → full analysis.
        Validates: Requirement 11.3
        """
        answers = [
            _make_answer("q-0", True),
            _make_answer("q-1", True),
            _make_answer("q-2", False),
            _make_answer("q-3", True),
            _make_answer("q-4", False),
        ]
        mock_answer_repository.get_by_user.return_value = answers

        domain_map = {
            "q-0": "Computer Vision",
            "q-1": "Computer Vision",
            "q-2": "Text Analysis",
            "q-3": "Text Analysis",
            "q-4": "Information Extraction",
        }

        async def get_by_id_side_effect(question_id, partition_key):
            domain = domain_map.get(question_id)
            if domain:
                return _make_question(question_id, domain)
            return None

        mock_question_repository.get_by_id.side_effect = get_by_id_side_effect

        result = await progress_service.calculate_progress("user-1")

        # Must NOT have insufficient_data flag
        assert "insufficient_data" not in result
        # Must have full progress data
        assert result["total_answered"] == 5
        assert result["overall_percentage"] == 60.0  # 3/5
        assert "per_domain" in result
        assert result["per_domain"]["Computer Vision"] == 100.0  # 2/2
        assert result["per_domain"]["Text Analysis"] == 50.0  # 1/2
        assert result["per_domain"]["Information Extraction"] == 0.0  # 0/1


class TestProgressWithZeroAnswers:
    """Verifies the exact return shape with 0 answers."""

    @pytest.mark.asyncio
    async def test_zero_answers_returns_exact_shape(
        self, progress_service, mock_answer_repository
    ):
        """With 0 answers, returns exactly the expected dict shape.

        Validates: Requirement 11.3
        """
        mock_answer_repository.get_by_user.return_value = []

        result = await progress_service.calculate_progress("user-1")

        assert result == {
            "total_answered": 0,
            "correct_count": 0,
            "insufficient_data": True,
        }


# --- Quality Score Deactivation Edge Case ---


class TestQualityScoreExactThreshold:
    """Tests for quality_score at exact threshold boundary."""

    @pytest.mark.asyncio
    async def test_quality_score_at_exact_threshold_not_deactivated(
        self, question_service, mock_question_repository
    ):
        """A question with quality_score exactly equal to the threshold must
        NOT be deactivated (uses strict less-than check).

        Validates: Requirement 15.5
        """
        threshold = 0.6
        mock_question_repository.get_active_by_certification.return_value = [
            {"id": "q-boundary", "quality_score": 0.6, "certification": "AI-103"},
        ]

        result = await question_service.deactivate_low_quality_questions(
            threshold, "AI-103"
        )

        assert result == []
        mock_question_repository.deactivate.assert_not_called()

    @pytest.mark.asyncio
    async def test_quality_score_just_below_threshold_deactivated(
        self, question_service, mock_question_repository
    ):
        """A question with quality_score epsilon below threshold must be deactivated.

        Validates: Requirement 15.5
        """
        threshold = 0.6
        mock_question_repository.get_active_by_certification.return_value = [
            {"id": "q-below", "quality_score": 0.5999, "certification": "AI-103"},
        ]
        mock_question_repository.deactivate.return_value = {
            "id": "q-below",
            "is_active": False,
        }

        result = await question_service.deactivate_low_quality_questions(
            threshold, "AI-103"
        )

        assert len(result) == 1
        mock_question_repository.deactivate.assert_called_once_with(
            "q-below", "AI-103"
        )


# --- Duplicate Detection Edge Case ---


class TestDuplicateDetectionIdenticalText:
    """Tests for duplicate detection with byte-for-byte identical text."""

    @pytest.mark.asyncio
    async def test_identical_text_raises_duplicate_error(
        self, question_service, mock_question_repository
    ):
        """A question with text identical to an existing question must raise
        DuplicateQuestionError.

        Validates: Requirement 3.5
        """
        identical_text = "What is the primary use of Azure AI Search?"

        mock_question_repository.get_active_by_certification.return_value = [
            {
                "id": "q-existing",
                "text": identical_text,
                "certification": "AI-103",
            }
        ]

        new_question = Question(
            id="q-new",
            certification="AI-103",
            domain="Information Extraction",
            text=identical_text,
            options=["Option A", "Option B", "Option C", "Option D"],
            correct_answer_index=0,
            short_explanation="Short explanation here.",
            detailed_explanation="Detailed explanation here.",
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(DuplicateQuestionError) as exc_info:
            await question_service.validate_and_persist_question(new_question)

        assert "q-existing" in str(exc_info.value)
        mock_question_repository.create.assert_not_called()
