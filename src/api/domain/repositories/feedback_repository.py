"""Feedback repository for CosmosDB operations on the question_feedback container.

Partition key: /user_id
"""

from azure.cosmos.aio import ContainerProxy

from src.api.domain.repositories.base_repository import BaseRepository


class FeedbackRepository(BaseRepository):
    """Repository for FeedbackRecord documents in the 'question_feedback' container.

    Partition key is /user_id, co-locating all of a user's feedback
    for efficient per-user queries.
    """

    def __init__(self, container: ContainerProxy) -> None:
        super().__init__(container)

    async def get_by_question(self, question_id: str, user_id: str) -> list[dict]:
        """Get all feedback records for a specific question by a user.

        Args:
            question_id: The question identifier.
            user_id: The user identifier (partition key).

        Returns:
            A list of feedback records for the question from the user.
        """
        query = (
            "SELECT * FROM c WHERE c.question_id = @question_id "
            "AND c.user_id = @user_id"
        )
        parameters = [
            {"name": "@question_id", "value": question_id},
            {"name": "@user_id", "value": user_id},
        ]
        return await self.query(query, parameters, partition_key=user_id)

    async def calculate_quality_score(self, question_id: str) -> float:
        """Calculate the quality score for a question based on all feedback.

        The quality score is defined as positive_count / total_count.
        Returns 1.0 if no feedback exists (default quality).

        This requires a cross-partition query since feedback is partitioned
        by user_id but we need to aggregate across all users for a question.

        Args:
            question_id: The question identifier.

        Returns:
            A float between 0.0 and 1.0 representing the quality score.
        """
        query = (
            "SELECT VALUE {"
            "'total': COUNT(1), "
            "'positive': COUNT(1) - ARRAY_LENGTH(ARRAY("
            "SELECT VALUE c.id FROM c WHERE c.question_id = @question_id "
            "AND c.rating != 'positive'"
            "))"
            "} FROM c WHERE c.question_id = @question_id"
        )
        # Use a simpler approach: fetch counts via two queries
        count_query = (
            "SELECT VALUE COUNT(1) FROM c WHERE c.question_id = @question_id"
        )
        positive_query = (
            "SELECT VALUE COUNT(1) FROM c "
            "WHERE c.question_id = @question_id AND c.rating = 'positive'"
        )
        parameters = [{"name": "@question_id", "value": question_id}]

        # Cross-partition queries to aggregate across all users
        total_count = 0
        query_iterable = self._container.query_items(
            query=count_query,
            parameters=parameters,
        )
        async for item in query_iterable:
            total_count = item

        if total_count == 0:
            return 1.0

        positive_count = 0
        query_iterable = self._container.query_items(
            query=positive_query,
            parameters=parameters,
        )
        async for item in query_iterable:
            positive_count = item

        return positive_count / total_count
