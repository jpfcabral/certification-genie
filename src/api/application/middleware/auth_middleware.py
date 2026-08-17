"""Authentication middleware for Telegram webhook signature verification.

Implements verification of the X-Telegram-Bot-Api-Secret-Token header against
the configured TELEGRAM_WEBHOOK_SECRET. Rejects requests with invalid or
missing signatures with HTTP 401.

Validates: Requirements 8.4, 8.5
"""

import hmac
from typing import Optional

from fastapi import HTTPException, Request

from src.api.infrastructure.config import get_settings


async def verify_telegram_webhook(request: Request) -> None:
    """FastAPI dependency that verifies Telegram webhook authenticity.

    Extracts the X-Telegram-Bot-Api-Secret-Token header from the incoming
    request and compares it against the configured webhook secret using
    constant-time comparison to prevent timing attacks.

    Raises:
        HTTPException: 401 if the header is missing or does not match
            the configured secret.
    """
    settings = get_settings()
    secret_token: Optional[str] = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token"
    )

    if secret_token is None:
        raise HTTPException(
            status_code=401,
            detail="Missing webhook signature",
        )

    if not hmac.compare_digest(secret_token, settings.TELEGRAM_WEBHOOK_SECRET):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )
