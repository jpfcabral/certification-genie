"""Session repository for CosmosDB operations on the sessions container.

Partition key: /user_id
"""

from typing import Optional

from azure.cosmos.aio import ContainerProxy

from src.api.domain.repositories.base_repository import BaseRepository


class SessionRepository(BaseRepository):
    """Repository for Session documents in CosmosDB.

    Partition key is /user_id, co-locating all of a user's sessions
    for efficient active-session lookups.
    """

    def __init__(self, container: ContainerProxy) -> None:
        super().__init__(container)

    async def get_active_session(self, user_id: str) -> Optional[dict]:
        """Get the currently active session for a user.

        Only one session should be active per user at a time.

        Args:
            user_id: The internal user identifier (partition key).

        Returns:
            The active session document, or None if no active session exists.
        """
        query = (
            "SELECT * FROM c WHERE c.user_id = @user_id "
            "AND c.is_active = true"
        )
        parameters = [{"name": "@user_id", "value": user_id}]
        results = await self.query(query, parameters, partition_key=user_id)
        return results[0] if results else None

    async def get_by_session_id(
        self, session_id: str, user_id: str
    ) -> Optional[dict]:
        """Get a session by its ID.

        Args:
            session_id: The session document ID.
            user_id: The user identifier (partition key).

        Returns:
            The session document, or None if not found.
        """
        return await self.get_by_id(session_id, partition_key=user_id)

    async def create_session(self, session_doc: dict) -> dict:
        """Create a new session document.

        Args:
            session_doc: The session document to persist.

        Returns:
            The created session document.
        """
        return await self.create(session_doc)

    async def update_session(self, session_doc: dict) -> dict:
        """Update an existing session document.

        Args:
            session_doc: The session document with updated fields.

        Returns:
            The updated session document.
        """
        return await self.upsert(session_doc)
