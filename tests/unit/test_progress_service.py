"""Unit tests for progress service.

Validates: Requirements 11.1, 11.2, 11.3, 17.3
"""

import pytest
from unittest.mock import AsyncMock

from src.api.application.services.progress_service import ProgressService


@pytest.fixture
def mock_answer_repository():
    """Create a mock AnswerRepository with AsyncMock methods."""
    repo = AsyncMock()
    repo.get_by_user = AsyncMock()
    return repo


@pytest.fixture
def mock_question_repository():
    """Create a mock QuestionRepository with AsyncMock methods."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def progress_service(mock_answer_repository, mock_question_repository):
    """Create a ProgressService with mocked repositories."""
    return ProgressService(
        answer_repository=mock_answer_repository,
        question_repository=mock_question_repository,
    )


def _make_answer(question_id: str, is_correct: bool) -> dict:
    """Helper to create an answer dict."""
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
    """Helper to create a question dict."""
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


class TestCalculateProgressInsufficientData:
    """Tests for calculate_progress with fewer than 5 answers."""

    @pytest.mark.asyncio
    async def test_zero_answers(self, progress_service, mock_answer_repository):
        """With 0 answers, should return insufficient_data flag."""
        mock_answer_repository.get_by_user.return_value = []

        result = await progress_service.calculate_progress("user-1")

        assert result["total_answered"] == 0
        assert result["correct_count"] == 0
        assert result["insufficient_data"] is True

    @pytest.mark.asyncio
    async def test_four_answers_insufficient(
        self, progress_service, mock_answer_repository
    ):
        """With 4 answers, should still return insufficient_data flag."""
        answers = [
            _make_answer(f"q-{i}", is_correct=(i % 2 == 0))
            for i in range(4)
        ]
        mock_answer_repository.get_by_user.return_value = answers

        result = await progress_service.calculate_progress("user-1")

        assert result["total_answered"] == 4
        assert result["correct_count"] == 2
        assert result["insufficient_data"] is True

    @pytest.mark.asyncio
    async def test_insufficient_data_has_no_per_domain(
        self, progress_service, mock_answer_repository
    ):
        """With insufficient data, result should not have per_domain."""
        mock_answer_repository.get_by_user.return_value = [
            _make_answer("q-1", True)
        ]

        result = await progress_service.calculate_progress("user-1")

        assert "per_domain" not in result
        assert "overall_percentage" not in result


class TestCalculateProgressSufficientData:
    """Tests for calculate_progress with 5 or more answers."""

    @pytest.mark.asyncio
    async def test_all_correct(
        self, progress_service, mock_answer_repository, mock_question_repository
    ):
        """With all answers correct, overall_percentage should be 100."""
        answers = [_make_answer(f"q-{i}", is_correct=True) for i in range(5)]
        mock_answer_repository.get_by_user.return_value = answers

        mock_question_repository.get_by_id.return_value = _make_question(
            "q-0", "Computer Vision"
        )

        result = await progress_service.calculate_progress("user-1")

        assert result["total_answered"] == 5
        assert result["overall_percentage"] == 100.0
        assert "insufficient_data" not in result

    @pytest.mark.asyncio
    async def test_mixed_correct_incorrect(
        self, progress_service, mock_answer_repository, mock_question_repository
    ):
        """With 3/5 correct, overall_percentage should be 60."""
        answers = [
            _make_answer("q-0", True),
            _make_answer("q-1", True),
            _make_answer("q-2", True),
            _make_answer("q-3", False),
            _make_answer("q-4", False),
        ]
        mock_answer_repository.get_by_user.return_value = answers

        mock_question_repository.get_by_id.return_value = _make_question(
            "q-0", "Text Analysis"
        )

        result = await progress_service.calculate_progress("user-1")

        assert result["total_answered"] == 5
        assert result["overall_percentage"] == 60.0

    @pytest.mark.asyncio
    async def test_per_domain_percentages(
        self, progress_service, mock_answer_repository, mock_question_repository
    ):
        """Per-domain percentages should be calculated correctly."""
        answers = [
            _make_answer("q-0", True),   # Computer Vision - correct
            _make_answer("q-1", False),  # Computer Vision - incorrect
            _make_answer("q-2", True),   # Text Analysis - correct
            _make_answer("q-3", True),   # Text Analysis - correct
            _make_answer("q-4", False),  # Text Analysis - incorrect
        ]
        mock_answer_repository.get_by_user.return_value = answers

        # Map question IDs to domains
        domain_map = {
            "q-0": "Computer Vision",
            "q-1": "Computer Vision",
            "q-2": "Text Analysis",
            "q-3": "Text Analysis",
            "q-4": "Text Analysis",
        }

        async def get_by_id_side_effect(question_id, partition_key):
            domain = domain_map.get(question_id)
            if domain:
                return _make_question(question_id, domain)
            return None

        mock_question_repository.get_by_id.side_effect = get_by_id_side_effect

        result = await progress_service.calculate_progress("user-1")

        assert result["per_domain"]["Computer Vision"] == 50.0  # 1/2
        assert abs(result["per_domain"]["Text Analysis"] - 66.666666) < 0.01  # 2/3


class TestGetWeakAreas:
    """Tests for get_weak_areas."""

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_limited(
        self, progress_service, mock_answer_repository
    ):
        """With fewer than 5 answers, returns insufficient_data dict."""
        mock_answer_repository.get_by_user.return_value = [
            _make_answer("q-1", True)
        ]

        result = await progress_service.get_weak_areas("user-1")

        assert isinstance(result, dict)
        assert result["insufficient_data"] is True

    @pytest.mark.asyncio
    async def test_returns_top_3_weakest(
        self, progress_service, mock_answer_repository, mock_question_repository
    ):
        """Should return the 3 domains with lowest percentages."""
        # Create answers across 4 domains with varying correctness
        answers = [
            # Domain A: 100% (2/2 correct)
            _make_answer("q-0", True),
            _make_answer("q-1", True),
            # Domain B: 50% (1/2 correct)
            _make_answer("q-2", True),
            _make_answer("q-3", False),
            # Domain C: 0% (0/2 correct)
            _make_answer("q-4", False),
            _make_answer("q-5", False),
            # Domain D: 33% (1/3 correct)
            _make_answer("q-6", True),
            _make_answer("q-7", False),
            _make_answer("q-8", False),
        ]
        mock_answer_repository.get_by_user.return_value = answers

        domain_map = {
            "q-0": "Generative AI and Agents",
            "q-1": "Generative AI and Agents",
            "q-2": "Computer Vision",
            "q-3": "Computer Vision",
            "q-4": "Text Analysis",
            "q-5": "Text Analysis",
            "q-6": "Information Extraction",
            "q-7": "Information Extraction",
            "q-8": "Information Extraction",
        }

        async def get_by_id_side_effect(question_id, partition_key):
            domain = domain_map.get(question_id)
            if domain:
                return _make_question(question_id, domain)
            return None

        mock_question_repository.get_by_id.side_effect = get_by_id_side_effect

        result = await progress_service.get_weak_areas("user-1")

        assert isinstance(result, list)
        assert len(result) == 3

        # Should be sorted ascending by percentage (weakest first)
        assert result[0]["domain"] == "Text Analysis"
        assert result[0]["percentage"] == 0.0

        assert result[1]["domain"] == "Information Extraction"
        assert abs(result[1]["percentage"] - 33.333) < 0.01

        assert result[2]["domain"] == "Computer Vision"
        assert result[2]["percentage"] == 50.0

    @pytest.mark.asyncio
    async def test_fewer_than_3_domains(
        self, progress_service, mock_answer_repository, mock_question_repository
    ):
        """With fewer than 3 domains, returns only the available ones."""
        answers = [
            _make_answer("q-0", True),
            _make_answer("q-1", False),
            _make_answer("q-2", True),
            _make_answer("q-3", False),
            _make_answer("q-4", True),
        ]
        mock_answer_repository.get_by_user.return_value = answers

        # All questions in the same domain
        mock_question_repository.get_by_id.return_value = _make_question(
            "q-0", "Computer Vision"
        )

        result = await progress_service.get_weak_areas("user-1")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["domain"] == "Computer Vision"
        assert result[0]["percentage"] == 60.0
