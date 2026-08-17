"""Scheduler module for daily study reminders.

Provides a function that can be called by an external scheduler
(APScheduler, cron job, or Azure Timer Trigger) to send daily
reminders to users who have not interacted with the bot in 24 hours
and have reminders enabled.

Usage with APScheduler:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from src.bot.scheduler import send_daily_reminders

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_reminders, "cron", hour=9, minute=0,
                      args=[bot, user_repository])
    scheduler.start()

Usage with a cron-triggered endpoint:
    @router.post("/cron/reminders")
    async def trigger_reminders():
        await send_daily_reminders(bot, user_repository)
"""

import logging
from datetime import datetime, timedelta, timezone

from telegram import Bot

from src.api.domain.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

REMINDER_MESSAGE = (
    "📚 *Daily Study Reminder*\n\n"
    "You haven't studied in a while! Keep your streak going.\n\n"
    "Use /train to practice questions or /flashcard for a quick review."
)

INACTIVITY_THRESHOLD_HOURS = 24


async def send_daily_reminders(
    bot: Bot,
    user_repository: UserRepository,
) -> int:
    """Send study reminders to inactive users.

    Queries all users who have reminders enabled and have not
    interacted with the bot in the last 24 hours. Sends each
    a motivational reminder message.

    This function is designed to be called by an external scheduler
    (APScheduler cron job, Azure Timer Trigger, or manual cron).

    Args:
        bot: The Telegram Bot instance for sending messages.
        user_repository: The user repository for querying users.

    Returns:
        The number of reminders successfully sent.
    """
    threshold = datetime.now(timezone.utc) - timedelta(
        hours=INACTIVITY_THRESHOLD_HOURS
    )

    inactive_users = await get_inactive_users(user_repository, threshold)

    sent_count = 0
    for user_doc in inactive_users:
        telegram_id = user_doc.get("telegram_id")
        if telegram_id is None:
            continue

        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=REMINDER_MESSAGE,
                parse_mode="Markdown",
            )
            sent_count += 1
            logger.info(
                "Sent daily reminder to user telegram_id=%d", telegram_id
            )
        except Exception:
            logger.warning(
                "Failed to send reminder to telegram_id=%d",
                telegram_id,
                exc_info=True,
            )

    logger.info(
        "Daily reminder job complete: %d reminders sent out of %d inactive users",
        sent_count,
        len(inactive_users),
    )

    return sent_count


async def get_inactive_users(
    user_repository: UserRepository,
    threshold: datetime,
) -> list[dict]:
    """Query users who are inactive and have reminders enabled.

    Returns users where:
    - reminders_enabled is True
    - last_interaction_at is either None (never interacted after registration)
      or older than the given threshold

    Args:
        user_repository: The user repository instance.
        threshold: The datetime cutoff — users whose last interaction
                   is before this time are considered inactive.

    Returns:
        A list of user document dicts matching the criteria.
    """
    query = (
        "SELECT * FROM c WHERE c.reminders_enabled = true "
        "AND (c.last_interaction_at = null "
        "OR c.last_interaction_at < @threshold)"
    )
    parameters = [{"name": "@threshold", "value": threshold.isoformat()}]

    items = []
    query_iterable = user_repository._container.query_items(
        query=query,
        parameters=parameters,
    )
    async for item in query_iterable:
        items.append(item)

    return items
