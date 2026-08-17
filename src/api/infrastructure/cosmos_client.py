"""Async CosmosDB client wrapper for Certification Genie.

Provides a singleton client with lazy container access for all collections.
Uses serverless connection mode (no connection pooling overhead).
"""

from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from azure.cosmos.aio._container import ContainerProxy
from azure.cosmos.aio._database import DatabaseProxy

from src.api.infrastructure.config import get_settings

DATABASE_NAME = "certification_genie"

CONTAINERS = {
    "users": "/id",
    "questions": "/certification",
    "user_questions": "/user_id",
    "question_feedback": "/user_id",
}


class CosmosDBClient:
    """Async CosmosDB client with container accessor methods.

    Initializes from the COSMOS_CONNECTION_STRING environment variable.
    Creates the database and containers on startup if they do not exist.
    Uses serverless connection mode (no provisioned throughput).
    """

    def __init__(self, connection_string: str | None = None) -> None:
        settings = get_settings()
        self._connection_string = connection_string or settings.COSMOS_CONNECTION_STRING
        self._client: CosmosClient | None = None
        self._database: DatabaseProxy | None = None
        self._containers: dict[str, ContainerProxy] = {}

    async def initialize(self) -> None:
        """Initialize the client, create database and containers if needed.

        Call this during application startup (e.g., FastAPI lifespan event).
        """
        self._client = CosmosClient.from_connection_string(
            self._connection_string
        )
        self._database = await self._client.create_database_if_not_exists(
            id=DATABASE_NAME
        )
        for container_name, partition_key_path in CONTAINERS.items():
            container = await self._database.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path=partition_key_path),
            )
            self._containers[container_name] = container

    async def close(self) -> None:
        """Close the underlying CosmosDB client connection.

        Call this during application shutdown.
        """
        if self._client:
            await self._client.close()
            self._client = None
            self._database = None
            self._containers.clear()

    def _get_container(self, name: str) -> ContainerProxy:
        """Retrieve a container proxy by name.

        Raises RuntimeError if the client has not been initialized.
        """
        if name not in self._containers:
            raise RuntimeError(
                f"Container '{name}' not available. "
                "Ensure CosmosDBClient.initialize() has been called."
            )
        return self._containers[name]

    @property
    def users(self) -> ContainerProxy:
        """Access the 'users' container (partition key: /id)."""
        return self._get_container("users")

    @property
    def questions(self) -> ContainerProxy:
        """Access the 'questions' container (partition key: /certification)."""
        return self._get_container("questions")

    @property
    def user_questions(self) -> ContainerProxy:
        """Access the 'user_questions' container (partition key: /user_id)."""
        return self._get_container("user_questions")

    @property
    def question_feedback(self) -> ContainerProxy:
        """Access the 'question_feedback' container (partition key: /user_id)."""
        return self._get_container("question_feedback")


_instance: CosmosDBClient | None = None


def get_cosmos_client() -> CosmosDBClient:
    """Return the module-level CosmosDB client singleton.

    Use as a FastAPI dependency or direct import.
    The client must be initialized via `initialize()` before accessing containers.
    """
    global _instance
    if _instance is None:
        _instance = CosmosDBClient()
    return _instance
