"""Application configuration loaded from environment variables.

Uses pydantic-settings to validate that all required environment variables
are present at startup, failing with clear error messages if any are missing.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All fields are required. The application will fail to start with a clear
    validation error if any environment variable is missing.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    COSMOS_CONNECTION_STRING: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_SECRET: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-5.4-mini"


def validate_settings() -> Settings:
    """Validate and return application settings.

    Call this during application startup to ensure all required environment
    variables are present. Raises a clear error if any are missing.

    Raises:
        SystemExit: If required environment variables are missing.
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as e:
        raise SystemExit(
            f"Configuration error: missing or invalid environment variables.\n{e}"
        ) from e


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton.

    Use as a FastAPI dependency:
        settings: Settings = Depends(get_settings)
    """
    return validate_settings()
