"""Unit tests for feedback service.

Validates: Requirements 15.3, 15.4, 15.7
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.api.application.services.feedback_service import FeedbackService
from src.api.domain.models.feedback_record import FeedbackRecord


@pytest.fixture
def mock_feedback_repository():
    """Create a mock FeedbackRepository with AsyncMock methods."""
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.calculate_quality_score = AsyncMock()
    repo._container = MagicMock()
    return repo


@pytest.fixture
def feedback_service(mock_feedback_repository):
    """Create a FeedbackService instance with a mocked repository."""
    return FeedbackService(feedback_repository=mock_feedback_repository)


class TestRecordFeedback:
    """Tests for record_feedback method."""

    @pytest.mark.asyncio
    async def test_record_feedback_creates_feedback_record(
        self, feedback_service, mock_feedback_repository
    ):
        """record_feedback should call repository create with correct data."""
        result = await feedback_service.record_feedback(
            user_id="user-123",
            question_id="q-001",
            rating="positive",
        )

        mock_feedback_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_feedback_returns_feedback_record(
        self, feedback_service, mock_feedback_repository
    ):
        """record_feedback should return a FeedbackRecord instance."""
        result = await feedback_service.record_feedback(
            user_id="user-123",
            question_id="q-001",
            rating="positive",
        )

        assert isinstance(result, FeedbackRecord)
        assert result.user_id == "user-123"
        assert result.question_id == "q-001"
        assert result.rating == "positive"

    @pytest.mark.asyncio
    async def test_record_feedback_generates_uuid(
        self, feedback_service, mock_feedback_repository
    ):
        """record_feedback should generate a UUID for the feedback record."""
        result = await feedback_service.record_feedback(
            user_id="user-123",
            question_id="q-001",
            rating="negative",
        )

        assert result.id is not None
        assert len(result.id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_record_feedback_sets_created_at(
        self, feedback_service, mock_feedback_repository
    ):
        """record_feedback should set created_at to current UTC time."""
        result = await feedback_service.record_feedback(
            user_id="user-123",
            question_id="q-001",
            rating="positive",
        )

        assert result.created_at is not None
        assert result.created_at.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_record_feedback_with_flag_type(
        self, feedback_service, mock_feedback_repository
    ):
        """record_feedback should persist optional flag_type."""
        result = await feedback_service.record_feedback(
            user_id="user-123",
            question_id="q-001",
            rating="negative",
            flag_type="incorrect_answer",
        )

        assert result.flag_type == "incorrect_answer"

    @pytest.mark.asyncio
    async def test_record_feedback_with_comment(
        self, feedback_service, mock_feedback_repository
    ):
        """record_feedback should persist optional comment."""
        result = await feedback_service.record_feedback(
            user_id="user-123",
            question_id="q-001",
            rating="negative",
            comment="The correct answer seems wrong",
        )

        assert result.comment == "The correct answer seems wrong"

    @pytest.mark.asyncio
    async def test_record_feedback_without_optional_fields(
        self, feedback_service, mock_feedback_repository
    ):
        """record_feedback should work without flag_type and comment."""
        result = await feedback_service.record_feedback(
            user_id="user-123",
            question_id="q-001",
            rating="positive",
        )

        assert result.flag_type is None
        assert result.comment is None


class TestCalculateQualityScore:
    """Tests for calculate_quality_score method."""

    @pytest.mark.asyncio
    async def test_delegates_to_repository(
        self, feedback_service, mock_feedback_repository
    ):
        """calculate_quality_score should delegate to repository."""
        mock_feedback_repository.calculate_quality_score.return_value = 0.85

        result = await feedback_service.calculate_quality_score("q-001")

        mock_feedback_repository.calculate_quality_score.assert_called_once_with("q-001")
        assert result == 0.85

    @pytest.mark.asyncio
    async def test_returns_default_when_no_feedback(
        self, feedback_service, mock_feedback_repository
    ):
        """calculate_quality_score should return 1.0 when no feedback exists."""
        mock_feedback_repository.calculate_quality_score.return_value = 1.0

        result = await feedback_service.calculate_quality_score("q-new")

        assert result == 1.0


class TestGetAggregatedFeedback:
    """Tests for get_aggregated_feedback method."""

    @pytest.mark.asyncio
    async def test_returns_aggregated_data(
        self, feedback_service, mock_feedback_repository
    ):
        """get_aggregated_feedback should return aggregated feedback dict."""
        # Mock the cross-partition query
        mock_items = [
            {"rating": "positive", "flag_type": None, "comment": None, "user_id": "u1"},
            {"rating": "positive", "flag_type": None, "comment": None, "user_id": "u2"},
            {"rating": "negative", "flag_type": "ambiguous", "comment": "Confusing", "user_id": "u3"},
        ]

        async def mock_async_iter(*args, **kwargs):
            for item in mock_items:
                yield item

        mock_feedback_repository._container.query_items.return_value = mock_async_iter()

        result = await feedback_service.get_aggregated_feedback("q-001")

        assert result["question_id"] == "q-001"
        assert result["total_count"] == 3
        assert result["positive_count"] == 2
        assert result["negative_count"] == 1
        assert result["flag_types"] == ["ambiguous"]
        assert result["comments"] == ["Confusing"]

    @pytest.mark.asyncio
    async def test_excludes_user_identifiers(
        self, feedback_service, mock_feedback_repository
    ):
        """get_aggregated_feedback should NOT include user_id in the result."""
        mock_items = [
            {"rating": "positive", "flag_type": None, "comment": None, "user_id": "secret-user-1"},
        ]

        async def mock_async_iter(*args, **kwargs):
            for item in mock_items:
                yield item

        mock_feedback_repository._container.query_items.return_value = mock_async_iter()

        result = await feedback_service.get_aggregated_feedback("q-001")

        # Verify no user_id fields exist in the result
        assert "user_id" not in result
        assert "user_ids" not in result

    @pytest.mark.asyncio
    async def test_empty_feedback(
        self, feedback_service, mock_feedback_repository
    ):
        """get_aggregated_feedback should handle questions with no feedback."""

        async def mock_async_iter(*args, **kwargs):
            return
            yield  # Make it an async generator

        mock_feedback_repository._container.query_items.return_value = mock_async_iter()

        result = await feedback_service.get_aggregated_feedback("q-new")

        assert result["total_count"] == 0
        assert result["positive_count"] == 0
        assert result["negative_count"] == 0
        assert result["flag_types"] == []
        assert result["comments"] == []

    @pytest.mark.asyncio
    async def test_cross_partition_query_enabled(
        self, feedback_service, mock_feedback_repository
    ):
        """get_aggregated_feedback should use cross-partition query."""

        async def mock_async_iter(*args, **kwargs):
            return
            yield

        mock_feedback_repository._container.query_items.return_value = mock_async_iter()

        await feedback_service.get_aggregated_feedback("q-001")

        mock_feedback_repository._container.query_items.assert_called_once()
        call_kwargs = mock_feedback_repository._container.query_items.call_args[1]
        assert call_kwargs["enable_cross_partition_query"] is True
