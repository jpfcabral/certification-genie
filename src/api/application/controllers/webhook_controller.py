"""Webhook controller for receiving Telegram updates.

Receives Telegram webhook POSTs, verifies signature, passes through
the Guardrail Agent, and dispatches to the python-telegram-bot Application
for full command/message handling with responses back to the user.
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from telegram import Update

from src.api.application.middleware.auth_middleware import verify_telegram_webhook

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])

WEBHOOK_TIMEOUT_SECONDS = 30


@router.post("/webhook", dependencies=[Depends(verify_telegram_webhook)])
async def handle_update(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    """Receive a Telegram webhook update and process it.

    The full pipeline:
    1. Verify webhook signature (via dependency)
    2. Parse the Telegram Update
    3. For free-text messages: run through Guardrail Agent
    4. Dispatch to python-telegram-bot handlers (which send responses)
    5. Return 200 to Telegram
    """
    payload: dict[str, Any] = await request.json()
    update_id = payload.get("update_id", "unknown")
    logger.info("Received webhook update %s", update_id)

    # Get the telegram bot application from app state
    bot_app = request.app.state.bot_app

    # Parse the update
    update = Update.de_json(payload, bot_app.bot)

    # Guardrail check for free-text (non-command) messages
    message = payload.get("message")
    text = message.get("text", "") if message else ""

    if text and not text.startswith("/"):
        guardrail_agent = request.app.state.guardrail_agent
        try:
            result = await guardrail_agent.ainvoke({"user_message": text})
            if not result.get("is_safe", True):
                logger.warning(
                    "Guardrail blocked update %s — reason: %s",
                    update_id,
                    result.get("block_reason", "unknown"),
                )
                # Send the fallback response directly
                chat_id = message.get("chat", {}).get("id")
                if chat_id:
                    await bot_app.bot.send_message(
                        chat_id=chat_id,
                        text=result.get("output_message", ""),
                    )
                return {"ok": True, "blocked": True}
        except Exception as e:
            logger.error("Guardrail error: %s", e)

    # Dispatch to python-telegram-bot handlers
    try:
        await asyncio.wait_for(
            bot_app.process_update(update),
            timeout=WEBHOOK_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("Update %s exceeded timeout", update_id)
    except Exception as e:
        logger.error("Error processing update %s: %s", update_id, e)

    return {"ok": True, "blocked": False}
