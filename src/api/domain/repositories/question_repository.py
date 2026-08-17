"""Question repository for CosmosDB operations on the questions container.

Partition key: /certification
"""

from typing import Optional

from azure.cosmos.aio import ContainerProxy

from src.api.domain.repositories.base_repository import BaseRepository


class QuestionRepository(BaseRepository):
    """Repository for Question documents in the 'questions' container.

    Partition key is /certification, enabling efficient queries
    for all questions within a specific certification.
    """

    def __init__(self, container: ContainerProxy) -> None:
        super().__init__(container)

    async def get_active_by_certification(self, certification: str) -> list[dict]:
        """Get all active questions for a given certification.

        Args:
            certification: The certification identifier (e.g., "AI-103").

        Returns:
            A list of active question documents.
        """
        query = (
            "SELECT * FROM c WHERE c.certification = @certification "
            "AND c.is_active = true"
        )
        parameters = [{"name": "@certification", "value": certification}]
        return await self.query(query, parameters, partition_key=certification)

    async def get_by_certification_and_domain(
        self, certification: str, domain: str
    ) -> list[dict]:
        """Get all questions for a certification filtered by domain.

        Args:
            certification: The certification identifier (e.g., "AI-103").
            domain: The domain name (e.g., "Generative AI and Agents").

        Returns:
            A list of question documents matching certification and domain.
        """
        query = (
            "SELECT * FROM c WHERE c.certification = @certification "
            "AND c.domain = @domain"
        )
        parameters = [
            {"name": "@certification", "value": certification},
            {"name": "@domain", "value": domain},
        ]
        return await self.query(query, parameters, partition_key=certification)

    async def deactivate(self, question_id: str, certification: str) -> Optional[dict]:
        """Deactivate a question by setting is_active to False.

        Args:
            question_id: The question document ID.
            certification: The certification (partition key value).

        Returns:
            The updated question document, or None if not found.
        """
        item = await self.get_by_id(question_id, partition_key=certification)
        if item is None:
            return None

        item["is_active"] = False
        return await self.upsert(item)
