"""Answer repository for CosmosDB operations on the user_questions container.

Partition key: /user_id
"""

from azure.cosmos.aio import ContainerProxy

from src.api.domain.repositories.base_repository import BaseRepository


class AnswerRepository(BaseRepository):
    """Repository for AnswerRecord documents in the 'user_questions' container.

    Partition key is /user_id, co-locating all of a user's answers
    for efficient progress queries.
    """

    def __init__(self, container: ContainerProxy) -> None:
        super().__init__(container)

    async def get_by_user(self, user_id: str) -> list[dict]:
        """Get all answer records for a given user.

        Args:
            user_id: The internal user identifier (partition key).

        Returns:
            A list of all answer record documents for the user.
        """
        query = "SELECT * FROM c WHERE c.user_id = @user_id"
        parameters = [{"name": "@user_id", "value": user_id}]
        return await self.query(query, parameters, partition_key=user_id)

    async def get_by_user_and_question(
        self, user_id: str, question_id: str
    ) -> list[dict]:
        """Get answer records for a specific user and question.

        A user may answer the same question multiple times across sessions.

        Args:
            user_id: The internal user identifier (partition key).
            question_id: The question identifier.

        Returns:
            A list of answer records for the user/question pair.
        """
        query = (
            "SELECT * FROM c WHERE c.user_id = @user_id "
            "AND c.question_id = @question_id"
        )
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@question_id", "value": question_id},
        ]
        return await self.query(query, parameters, partition_key=user_id)

    async def get_answered_question_ids(self, user_id: str) -> list[str]:
        """Get the set of question IDs that a user has answered.

        Useful for the Orchestrator to prioritize unanswered questions.

        Args:
            user_id: The internal user identifier (partition key).

        Returns:
            A list of distinct question IDs the user has answered.
        """
        query = "SELECT DISTINCT VALUE c.question_id FROM c WHERE c.user_id = @user_id"
        parameters = [{"name": "@user_id", "value": user_id}]

        items = []
        query_iterable = self._container.query_items(
            query=query,
            parameters=parameters,
            partition_key=user_id,
        )
        async for item in query_iterable:
            items.append(item)

        return items
