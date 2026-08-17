"""Base repository with generic async CRUD operations for CosmosDB.

Provides get_by_id, create, query, upsert, and delete operations with
automatic retry logic for transient errors (HTTP 429 and 503) using
exponential backoff.
"""

import asyncio
import logging
from typing import Any, Generic, Optional, TypeVar

from azure.cosmos.aio import ContainerProxy
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Transient HTTP status codes that warrant a retry
_TRANSIENT_STATUS_CODES = (429, 503)

# Default retry configuration
_MAX_RETRIES = 3
_BASE_DELAY_SECONDS = 1.0
_MAX_DELAY_SECONDS = 16.0


class BaseRepository(Generic[T]):
    """Base repository wrapping CosmosDB container operations.

    Provides generic async CRUD methods with retry logic for transient
    errors (429 Too Many Requests, 503 Service Unavailable) using
    exponential backoff.

    Args:
        container: An async CosmosDB ContainerProxy instance.
    """

    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    async def _retry_operation(self, operation, *args, **kwargs) -> Any:
        """Execute an operation with retry logic for transient errors.

        Uses exponential backoff with a maximum delay cap. For HTTP 429
        responses, respects the server-suggested retry-after header when
        available.

        Args:
            operation: The async callable to execute.
            *args: Positional arguments for the operation.
            **kwargs: Keyword arguments for the operation.

        Returns:
            The result of the operation.

        Raises:
            CosmosHttpResponseError: If all retries are exhausted or a
                non-transient error occurs.
        """
        last_exception: Optional[CosmosHttpResponseError] = None

        for attempt in range(_MAX_RETRIES):
            try:
                return await operation(*args, **kwargs)
            except CosmosHttpResponseError as e:
                if e.status_code not in _TRANSIENT_STATUS_CODES:
                    raise

                last_exception = e
                if attempt == _MAX_RETRIES - 1:
                    break

                # Use retry-after header for 429, or exponential backoff
                delay = _BASE_DELAY_SECONDS * (2**attempt)
                if e.status_code == 429 and hasattr(e, "headers"):
                    retry_after = e.headers.get("x-ms-retry-after-ms")
                    if retry_after:
                        delay = int(retry_after) / 1000.0

                delay = min(delay, _MAX_DELAY_SECONDS)
                logger.warning(
                    "Transient error (HTTP %d) on attempt %d/%d. "
                    "Retrying in %.1fs.",
                    e.status_code,
                    attempt + 1,
                    _MAX_RETRIES,
                    delay,
                )
                await asyncio.sleep(delay)

        raise last_exception  # type: ignore[misc]

    async def get_by_id(self, id: str, partition_key: str) -> Optional[dict]:
        """Retrieve a document by its ID and partition key.

        Args:
            id: The document ID.
            partition_key: The partition key value.

        Returns:
            The document as a dict, or None if not found.
        """
        try:
            item = await self._retry_operation(
                self._container.read_item,
                item=id,
                partition_key=partition_key,
            )
            return item
        except CosmosResourceNotFoundError:
            return None

    async def create(self, item: dict) -> dict:
        """Create a new document in the container.

        Args:
            item: The document to create as a dict.

        Returns:
            The created document with CosmosDB metadata.

        Raises:
            CosmosHttpResponseError: If creation fails (e.g., conflict).
        """
        result = await self._retry_operation(
            self._container.create_item,
            body=item,
        )
        return result

    async def query(
        self, query: str, parameters: list, partition_key: str
    ) -> list[dict]:
        """Execute a SQL query against the container.

        Args:
            query: CosmosDB SQL query string.
            parameters: List of query parameter dicts with 'name' and 'value'.
            partition_key: The partition key value to scope the query.

        Returns:
            A list of matching documents.
        """
        items = []
        query_iterable = self._container.query_items(
            query=query,
            parameters=parameters,
            partition_key=partition_key,
        )
        async for item in query_iterable:
            items.append(item)
        return items

    async def upsert(self, item: dict) -> dict:
        """Create or update a document in the container.

        If a document with the same ID exists, it will be replaced.
        Otherwise, a new document is created.

        Args:
            item: The document to upsert as a dict.

        Returns:
            The upserted document with CosmosDB metadata.
        """
        result = await self._retry_operation(
            self._container.upsert_item,
            body=item,
        )
        return result

    async def delete(self, id: str, partition_key: str) -> None:
        """Delete a document by its ID and partition key.

        Args:
            id: The document ID to delete.
            partition_key: The partition key value.

        Raises:
            CosmosResourceNotFoundError: If the document does not exist.
        """
        await self._retry_operation(
            self._container.delete_item,
            item=id,
            partition_key=partition_key,
        )
