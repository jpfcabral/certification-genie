"""Unit tests for the infrastructure layer.

Tests configuration loading/validation and repository query construction.

Validates: Requirements 16.5, 16.6
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call

from pydantic import ValidationError

from src.api.infrastructure.config import Settings, get_settings


# --- Required env vars for a valid configuration ---

_REQUIRED_ENV_VARS = {
    "COSMOS_CONNECTION_STRING": "AccountEndpoint=https://test.documents.azure.com:443/;AccountKey=dGVzdA==;",
    "TELEGRAM_BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    "TELEGRAM_WEBHOOK_SECRET": "my-webhook-secret",
    "OPENAI_API_KEY": "sk-test-key-1234567890",
}


# --- Config: startup fails with missing required env vars ---


class TestConfigMissingEnvVars:
    """Test that Settings raises ValidationError when required env vars are missing."""

    def test_fails_when_all_vars_missing(self, monkeypatch):
        """Settings() raises ValidationError when no env vars are set."""
        # Clear all relevant env vars
        for var in _REQUIRED_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        # Prevent loading from .env file
        monkeypatch.setattr(Settings, "model_config", {
            "env_file": None,
            "env_file_encoding": "utf-8",
            "case_sensitive": True,
        })
        get_settings.cache_clear()

        with pytest.raises(ValidationError):
            Settings()

    @pytest.mark.parametrize("missing_var", _REQUIRED_ENV_VARS.keys())
    def test_fails_when_single_var_missing(self, monkeypatch, missing_var):
        """Settings() raises ValidationError when any single required var is missing."""
        # Set all vars except the one being tested
        for var, value in _REQUIRED_ENV_VARS.items():
            if var != missing_var:
                monkeypatch.setenv(var, value)
            else:
                monkeypatch.delenv(var, raising=False)
        # Prevent loading from .env file
        monkeypatch.setattr(Settings, "model_config", {
            "env_file": None,
            "env_file_encoding": "utf-8",
            "case_sensitive": True,
        })
        get_settings.cache_clear()

        with pytest.raises(ValidationError):
            Settings()


# --- Config: loads all values correctly from env ---


class TestConfigLoadsCorrectly:
    """Test that Settings loads all values correctly when env vars are present."""

    def test_loads_all_values_from_env(self, monkeypatch):
        """Settings() correctly loads all required env vars."""
        for var, value in _REQUIRED_ENV_VARS.items():
            monkeypatch.setenv(var, value)
        # Prevent loading from .env file
        monkeypatch.setattr(Settings, "model_config", {
            "env_file": None,
            "env_file_encoding": "utf-8",
            "case_sensitive": True,
        })
        get_settings.cache_clear()

        settings = Settings()

        assert settings.COSMOS_CONNECTION_STRING == _REQUIRED_ENV_VARS["COSMOS_CONNECTION_STRING"]
        assert settings.TELEGRAM_BOT_TOKEN == _REQUIRED_ENV_VARS["TELEGRAM_BOT_TOKEN"]
        assert settings.TELEGRAM_WEBHOOK_SECRET == _REQUIRED_ENV_VARS["TELEGRAM_WEBHOOK_SECRET"]
        assert settings.OPENAI_API_KEY == _REQUIRED_ENV_VARS["OPENAI_API_KEY"]

    def test_get_settings_returns_cached_instance(self, monkeypatch):
        """get_settings() returns the same cached instance on multiple calls."""
        for var, value in _REQUIRED_ENV_VARS.items():
            monkeypatch.setenv(var, value)
        monkeypatch.setattr(Settings, "model_config", {
            "env_file": None,
            "env_file_encoding": "utf-8",
            "case_sensitive": True,
        })
        get_settings.cache_clear()

        first = get_settings()
        second = get_settings()

        assert first is second


# --- Repository: query builds correct CosmosDB SQL ---


class TestQuestionRepositoryQueries:
    """Test that QuestionRepository builds correct CosmosDB SQL queries."""

    @pytest.mark.asyncio
    async def test_get_active_by_certification_query(self):
        """get_active_by_certification passes correct SQL and parameters."""
        from src.api.domain.repositories.question_repository import QuestionRepository

        container = AsyncMock()
        # Mock the async iterator for query_items
        async def mock_query_items(*args, **kwargs):
            for item in []:
                yield item

        container.query_items = MagicMock(return_value=mock_query_items())
        repo = QuestionRepository(container)

        await repo.get_active_by_certification("AI-103")

        container.query_items.assert_called_once_with(
            query=(
                "SELECT * FROM c WHERE c.certification = @certification "
                "AND c.is_active = true"
            ),
            parameters=[{"name": "@certification", "value": "AI-103"}],
            partition_key="AI-103",
        )

    @pytest.mark.asyncio
    async def test_get_by_certification_and_domain_query(self):
        """get_by_certification_and_domain passes correct SQL and parameters."""
        from src.api.domain.repositories.question_repository import QuestionRepository

        container = AsyncMock()
        async def mock_query_items(*args, **kwargs):
            for item in []:
                yield item

        container.query_items = MagicMock(return_value=mock_query_items())
        repo = QuestionRepository(container)

        await repo.get_by_certification_and_domain("AI-103", "Computer Vision")

        container.query_items.assert_called_once_with(
            query=(
                "SELECT * FROM c WHERE c.certification = @certification "
                "AND c.domain = @domain"
            ),
            parameters=[
                {"name": "@certification", "value": "AI-103"},
                {"name": "@domain", "value": "Computer Vision"},
            ],
            partition_key="AI-103",
        )


class TestAnswerRepositoryQueries:
    """Test that AnswerRepository builds correct CosmosDB SQL queries."""

    @pytest.mark.asyncio
    async def test_get_by_user_query(self):
        """get_by_user passes correct SQL and parameters."""
        from src.api.domain.repositories.answer_repository import AnswerRepository

        container = AsyncMock()
        async def mock_query_items(*args, **kwargs):
            for item in []:
                yield item

        container.query_items = MagicMock(return_value=mock_query_items())
        repo = AnswerRepository(container)

        await repo.get_by_user("user-001")

        container.query_items.assert_called_once_with(
            query="SELECT * FROM c WHERE c.user_id = @user_id",
            parameters=[{"name": "@user_id", "value": "user-001"}],
            partition_key="user-001",
        )

    @pytest.mark.asyncio
    async def test_get_by_user_and_question_query(self):
        """get_by_user_and_question passes correct SQL and parameters."""
        from src.api.domain.repositories.answer_repository import AnswerRepository

        container = AsyncMock()
        async def mock_query_items(*args, **kwargs):
            for item in []:
                yield item

        container.query_items = MagicMock(return_value=mock_query_items())
        repo = AnswerRepository(container)

        await repo.get_by_user_and_question("user-001", "q-005")

        container.query_items.assert_called_once_with(
            query=(
                "SELECT * FROM c WHERE c.user_id = @user_id "
                "AND c.question_id = @question_id"
            ),
            parameters=[
                {"name": "@user_id", "value": "user-001"},
                {"name": "@question_id", "value": "q-005"},
            ],
            partition_key="user-001",
        )

    @pytest.mark.asyncio
    async def test_get_answered_question_ids_query(self):
        """get_answered_question_ids passes correct SQL for distinct question IDs."""
        from src.api.domain.repositories.answer_repository import AnswerRepository

        container = AsyncMock()
        async def mock_query_items(*args, **kwargs):
            for item in ["q-001", "q-002"]:
                yield item

        container.query_items = MagicMock(return_value=mock_query_items())
        repo = AnswerRepository(container)

        result = await repo.get_answered_question_ids("user-001")

        assert result == ["q-001", "q-002"]
        container.query_items.assert_called_once_with(
            query="SELECT DISTINCT VALUE c.question_id FROM c WHERE c.user_id = @user_id",
            parameters=[{"name": "@user_id", "value": "user-001"}],
            partition_key="user-001",
        )


class TestFeedbackRepositoryQueries:
    """Test that FeedbackRepository builds correct CosmosDB SQL queries."""

    @pytest.mark.asyncio
    async def test_get_by_question_query(self):
        """get_by_question passes correct SQL and parameters."""
        from src.api.domain.repositories.feedback_repository import FeedbackRepository

        container = AsyncMock()
        async def mock_query_items(*args, **kwargs):
            for item in []:
                yield item

        container.query_items = MagicMock(return_value=mock_query_items())
        repo = FeedbackRepository(container)

        await repo.get_by_question("q-001", "user-001")

        container.query_items.assert_called_once_with(
            query=(
                "SELECT * FROM c WHERE c.question_id = @question_id "
                "AND c.user_id = @user_id"
            ),
            parameters=[
                {"name": "@question_id", "value": "q-001"},
                {"name": "@user_id", "value": "user-001"},
            ],
            partition_key="user-001",
        )
