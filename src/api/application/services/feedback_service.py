"""Feedback service for recording and aggregating question quality feedback.

Handles persisting user feedback on questions, calculating quality scores,
and providing aggregated feedback data (without user identifiers) to the
Generator Agent for improving question generation.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from src.api.domain.models.feedback_record import FeedbackRecord
from src.api.domain.repositories.feedback_repository import FeedbackRepository


class FeedbackService:
    """Service for question quality feedback operations.

    Provides methods to record user feedback, calculate quality scores,
    and retrieve aggregated feedback without user identifiers.
    """

    def __init__(self, feedback_repository: FeedbackRepository) -> None:
        self._repository = feedback_repository

    async def record_feedback(
        self,
        user_id: str,
        question_id: str,
        rating: str,
        flag_type: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> FeedbackRecord:
        """Record user feedback on a question.

        Creates a FeedbackRecord with a generated UUID and current timestamp,
        then persists it via the repository.

        Args:
            user_id: The user's internal identifier (partition key).
            question_id: The question being rated.
            rating: Either "positive" or "negative".
            flag_type: Optional flag category (e.g., "incorrect_answer",
                "ambiguous", "too_easy", "too_hard", "off_topic").
            comment: Optional text comment (max 200 characters).

        Returns:
            The created FeedbackRecord.
        """
        feedback = FeedbackRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            question_id=question_id,
            rating=rating,
            flag_type=flag_type,
            comment=comment,
            created_at=datetime.now(timezone.utc),
        )

        await self._repository.create(feedback.model_dump(mode="json"))

        return feedback

    async def calculate_quality_score(self, question_id: str) -> float:
        """Calculate the quality score for a question.

        Delegates to the repository's cross-partition quality score
        calculation. The score is positive_count / total_count.
        Returns 1.0 if no feedback exists.

        Args:
            question_id: The question identifier.

        Returns:
            A float between 0.0 and 1.0 representing the quality score.
        """
        return await self._repository.calculate_quality_score(question_id)

    async def get_aggregated_feedback(self, question_id: str) -> dict:
        """Get aggregated feedback for a question without user identifiers.

        Fetches all feedback records for a question across all users
        (cross-partition query) and returns aggregated data suitable
        for the Generator Agent. User IDs are stripped to maintain
        data privacy per requirement 15.7.

        Args:
            question_id: The question identifier.

        Returns:
            A dict containing:
                - question_id: The question identifier.
                - total_count: Total number of feedback records.
                - positive_count: Number of positive ratings.
                - negative_count: Number of negative ratings.
                - flag_types: List of flag categories reported.
                - comments: List of non-null comments (no user attribution).
        """
        # Cross-partition query to get all feedback for the question
        query = "SELECT * FROM c WHERE c.question_id = @question_id"
        parameters = [{"name": "@question_id", "value": question_id}]

        records: list[dict] = []
        query_iterable = self._repository._container.query_items(
            query=query,
            parameters=parameters,
        )
        async for item in query_iterable:
            records.append(item)

        total_count = len(records)
        positive_count = sum(1 for r in records if r.get("rating") == "positive")
        negative_count = total_count - positive_count

        flag_types = [
            r["flag_type"] for r in records if r.get("flag_type") is not None
        ]

        comments = [
            r["comment"] for r in records if r.get("comment") is not None
        ]

        return {
            "question_id": question_id,
            "total_count": total_count,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "flag_types": flag_types,
            "comments": comments,
        }
