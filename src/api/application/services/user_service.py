"""User service with idempotent registration.

Handles user registration ensuring no duplicate records are created
for the same Telegram user. Stores only minimal data: internal UUID,
numeric telegram_id, and registration date.
"""

import uuid
from datetime import datetime, timezone

from src.api.domain.models.user import User
from src.api.domain.repositories.user_repository import UserRepository


class UserService:
    """Service for user registration and retrieval.

    Provides idempotent registration: calling register_or_get_user
    with the same telegram_id always returns the same user without
    creating duplicates.
    """

    def __init__(self, user_repository: UserRepository) -> None:
        self._repository = user_repository

    async def register_or_get_user(self, telegram_id: int) -> User:
        """Register a new user or return the existing one.

        If a user with the given telegram_id already exists, updates
        their last_interaction_at timestamp and returns the existing user.
        If no user exists, creates a new one with a generated UUID and
        the current timestamp as registered_at.

        Args:
            telegram_id: The numeric Telegram user identifier.

        Returns:
            A User model instance (either existing or newly created).
        """
        existing = await self._repository.get_by_telegram_id(telegram_id)

        if existing is not None:
            # Update last_interaction_at for the existing user
            existing["last_interaction_at"] = datetime.now(timezone.utc).isoformat()
            await self._repository.update_user(existing)
            return User(**{
                "id": existing["id"],
                "telegram_id": existing["telegram_id"],
                "registered_at": existing["registered_at"],
                "reminders_enabled": existing.get("reminders_enabled", True),
                "last_interaction_at": existing["last_interaction_at"],
            })

        # Create new user with minimal data
        now = datetime.now(timezone.utc)
        new_user = User(
            id=str(uuid.uuid4()),
            telegram_id=telegram_id,
            registered_at=now,
        )

        user_doc = new_user.model_dump(mode="json")
        await self._repository.create_user(user_doc)

        return new_user
