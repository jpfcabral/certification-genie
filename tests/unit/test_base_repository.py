"""Unit tests for the base repository CosmosDB operations and retry logic.

Validates: Requirements 13.1, 13.6
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

from src.api.domain.repositories.base_repository import (
    BaseRepository,
    _MAX_RETRIES,
    _TRANSIENT_STATUS_CODES,
)


# --- Helpers ---


def _make_cosmos_error(status_code: int) -> CosmosHttpResponseError:
    """Create a CosmosHttpResponseError with the given status code."""
    error = CosmosHttpResponseError(status_code=status_code, message="test error")
    error.headers = {}
    return error


def _make_repo(container_mock: AsyncMock) -> BaseRepository:
    """Create a BaseRepository with a mocked container."""
    return BaseRepository(container=container_mock)


# --- get_by_id ---


class TestGetById:
    @pytest.mark.asyncio
    async def test_returns_item_when_found(self):
        container = AsyncMock()
        expected = {"id": "doc-1", "name": "test"}
        container.read_item = AsyncMock(return_value=expected)
        repo = _make_repo(container)

        result = await repo.get_by_id("doc-1", partition_key="pk-1")

        assert result == expected
        container.read_item.assert_called_once_with(
            item="doc-1", partition_key="pk-1"
        )

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        container = AsyncMock()
        container.read_item = AsyncMock(
            side_effect=CosmosResourceNotFoundError()
        )
        repo = _make_repo(container)

        result = await repo.get_by_id("missing-id", partition_key="pk-1")

        assert result is None


# --- create ---


class TestCreate:
    @pytest.mark.asyncio
    async def test_creates_and_returns_item(self):
        container = AsyncMock()
        doc = {"id": "new-1", "data": "value"}
        container.create_item = AsyncMock(return_value=doc)
        repo = _make_repo(container)

        result = await repo.create(doc)

        assert result == doc
        container.create_item.assert_called_once_with(body=doc)


# --- query ---


class TestQuery:
    @pytest.mark.asyncio
    async def test_returns_matching_items(self):
        container = AsyncMock()
        items = [{"id": "1"}, {"id": "2"}]

        # Mock the async iterator returned by query_items
        async def mock_query_items(*args, **kwargs):
            for item in items:
                yield item

        container.query_items = MagicMock(return_value=mock_query_items())
        repo = _make_repo(container)

        result = await repo.query(
            query="SELECT * FROM c WHERE c.active = @active",
            parameters=[{"name": "@active", "value": True}],
            partition_key="pk-1",
        )

        assert result == items
        container.query_items.assert_called_once_with(
            query="SELECT * FROM c WHERE c.active = @active",
            parameters=[{"name": "@active", "value": True}],
            partition_key="pk-1",
        )


# --- upsert ---


class TestUpsert:
    @pytest.mark.asyncio
    async def test_upserts_and_returns_item(self):
        container = AsyncMock()
        doc = {"id": "upsert-1", "data": "updated"}
        container.upsert_item = AsyncMock(return_value=doc)
        repo = _make_repo(container)

        result = await repo.upsert(doc)

        assert result == doc
        container.upsert_item.assert_called_once_with(body=doc)


# --- delete ---


class TestDelete:
    @pytest.mark.asyncio
    async def test_deletes_item(self):
        container = AsyncMock()
        container.delete_item = AsyncMock(return_value=None)
        repo = _make_repo(container)

        await repo.delete("doc-1", partition_key="pk-1")

        container.delete_item.assert_called_once_with(
            item="doc-1", partition_key="pk-1"
        )


# --- Retry logic ---


class TestRetryLogic:
    @pytest.mark.asyncio
    @patch("src.api.domain.repositories.base_repository.asyncio.sleep", new_callable=AsyncMock)
    async def test_retries_on_429(self, mock_sleep):
        container = AsyncMock()
        error_429 = _make_cosmos_error(429)
        expected = {"id": "doc-1"}

        # Fail twice with 429, succeed on third attempt
        container.read_item = AsyncMock(
            side_effect=[error_429, error_429, expected]
        )
        repo = _make_repo(container)

        result = await repo.get_by_id("doc-1", partition_key="pk-1")

        assert result == expected
        assert container.read_item.call_count == 3
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    @patch("src.api.domain.repositories.base_repository.asyncio.sleep", new_callable=AsyncMock)
    async def test_retries_on_503(self, mock_sleep):
        container = AsyncMock()
        error_503 = _make_cosmos_error(503)
        expected = {"id": "doc-1"}

        # Fail once with 503, succeed on second attempt
        container.read_item = AsyncMock(
            side_effect=[error_503, expected]
        )
        repo = _make_repo(container)

        result = await repo.get_by_id("doc-1", partition_key="pk-1")

        assert result == expected
        assert container.read_item.call_count == 2
        assert mock_sleep.call_count == 1

    @pytest.mark.asyncio
    @patch("src.api.domain.repositories.base_repository.asyncio.sleep", new_callable=AsyncMock)
    async def test_raises_after_max_retries_exhausted(self, mock_sleep):
        container = AsyncMock()
        error_429 = _make_cosmos_error(429)

        # Fail all attempts
        container.read_item = AsyncMock(
            side_effect=[error_429] * _MAX_RETRIES
        )
        repo = _make_repo(container)

        with pytest.raises(CosmosHttpResponseError) as exc_info:
            await repo.get_by_id("doc-1", partition_key="pk-1")

        assert exc_info.value.status_code == 429
        assert container.read_item.call_count == _MAX_RETRIES

    @pytest.mark.asyncio
    async def test_does_not_retry_non_transient_error(self):
        container = AsyncMock()
        error_400 = _make_cosmos_error(400)
        container.read_item = AsyncMock(side_effect=error_400)
        repo = _make_repo(container)

        with pytest.raises(CosmosHttpResponseError) as exc_info:
            await repo.get_by_id("doc-1", partition_key="pk-1")

        assert exc_info.value.status_code == 400
        # Should not retry — only one call
        assert container.read_item.call_count == 1

    @pytest.mark.asyncio
    @patch("src.api.domain.repositories.base_repository.asyncio.sleep", new_callable=AsyncMock)
    async def test_exponential_backoff_delays(self, mock_sleep):
        container = AsyncMock()
        error_503 = _make_cosmos_error(503)
        expected = {"id": "doc-1"}

        # Fail twice, succeed on third
        container.read_item = AsyncMock(
            side_effect=[error_503, error_503, expected]
        )
        repo = _make_repo(container)

        await repo.get_by_id("doc-1", partition_key="pk-1")

        # Verify exponential backoff: 1s, 2s
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays[0] == 1.0  # 1 * 2^0
        assert delays[1] == 2.0  # 1 * 2^1

    @pytest.mark.asyncio
    @patch("src.api.domain.repositories.base_repository.asyncio.sleep", new_callable=AsyncMock)
    async def test_respects_retry_after_header_for_429(self, mock_sleep):
        container = AsyncMock()
        error_429 = _make_cosmos_error(429)
        error_429.headers = {"x-ms-retry-after-ms": "500"}
        expected = {"id": "doc-1"}

        container.read_item = AsyncMock(
            side_effect=[error_429, expected]
        )
        repo = _make_repo(container)

        await repo.get_by_id("doc-1", partition_key="pk-1")

        # Should use 500ms (0.5s) from header instead of default backoff
        mock_sleep.assert_called_once_with(0.5)
