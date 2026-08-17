"""User repository for CosmosDB operations on the users container.

Partition key: /id
"""

from typing import Optional

from azure.cosmos.aio import ContainerProxy

from src.api.domain.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    """Repository for User documents in the 'users' container.

    Partition key is /id (internal UUID), ensuring each user is
    isolated in their own logical partition.
    """

    def __init__(self, container: ContainerProxy) -> None:
        super().__init__(container)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[dict]:
        """Find a user by their Telegram numeric identifier.

        Uses a cross-partition query since telegram_id is not the partition key.

        Args:
            telegram_id: The numeric Telegram user ID.

        Returns:
            The user document dict, or None if not found.
        """
        query = "SELECT * FROM c WHERE c.telegram_id = @telegram_id"
        parameters = [{"name": "@telegram_id", "value": telegram_id}]

        items = []
        query_iterable = self._container.query_items(
            query=query,
            parameters=parameters,
        )
        async for item in query_iterable:
            items.append(item)

        return items[0] if items else None

    async def create_user(self, user: dict) -> dict:
        """Create a new user document.

        Args:
            user: The user document dict containing at minimum
                  id, telegram_id, and registered_at.

        Returns:
            The created user document with CosmosDB metadata.
        """
        return await self.create(user)

    async def update_user(self, user: dict) -> dict:
        """Update an existing user document via upsert.

        Args:
            user: The full user document dict with updated fields.

        Returns:
            The updated user document.
        """
        return await self.upsert(user)
