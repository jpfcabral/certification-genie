"""Main application entrypoint for Certification Genie.

Creates the FastAPI application with:
- Telegram Bot Application (python-telegram-bot) for handling commands
- Guardrail Agent for input safety screening
- CosmosDB client for persistence
- Webhook + health routers
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    filters,
)

from src.ai.agents.guardrail_agent.graph import build_guardrail_graph
from src.api.application.controllers.health_controller import (
    router as health_router,
)
from src.api.application.controllers.webhook_controller import (
    router as webhook_router,
)
from src.api.infrastructure.config import get_settings, validate_settings
from src.api.infrastructure.cosmos_client import get_cosmos_client
from src.bot.handlers.command_handler import (
    handle_start,
    handle_train,
    handle_simulate,
    handle_ask,
    handle_progress,
    handle_exit,
    handle_flashcard,
    handle_domains,
    handle_weak_areas,
    handle_reminders,
)
from src.bot.handlers.message_handler import handle_message
from src.bot.handlers.callback_handler import handle_callback_query
from src.bot.handlers.poll_handler import handle_poll_answer

logger = logging.getLogger(__name__)


async def _build_bot_app(settings) -> Application:
    """Build and initialize the python-telegram-bot Application.

    Registers all command, message, callback, and poll handlers.
    Uses bot_data to share service instances with handlers.
    """
    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Register command handlers
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("train", handle_train))
    app.add_handler(CommandHandler("simulate", handle_simulate))
    app.add_handler(CommandHandler("ask", handle_ask))
    app.add_handler(CommandHandler("progress", handle_progress))
    app.add_handler(CommandHandler("exit", handle_exit))
    app.add_handler(CommandHandler("end_simulation", handle_exit))
    app.add_handler(CommandHandler("flashcard", handle_flashcard))
    app.add_handler(CommandHandler("domains", handle_domains))
    app.add_handler(CommandHandler("weak_areas", handle_weak_areas))
    app.add_handler(CommandHandler("reminders", handle_reminders))

    # Callback query handler (inline keyboard buttons)
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Poll answer handler
    app.add_handler(PollAnswerHandler(handle_poll_answer))

    # Free-text message handler (must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Error handler — logs all exceptions from handlers
    async def error_handler(update, context):
        import traceback, sys
        tb = "".join(traceback.format_exception(type(context.error), context.error, context.error.__traceback__))
        print(f"[BOT ERROR] {context.error}\n{tb}", file=sys.stderr, flush=True)
        logger.error("Exception in handler: %s\n%s", context.error, tb)

    app.add_error_handler(error_handler)

    # Initialize the bot application (required before processing updates)
    await app.initialize()

    return app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown."""
    logger.info("Starting Certification Genie API...")

    # 1. Validate config
    settings = validate_settings()
    logger.info("Configuration validated")

    # 2. Initialize CosmosDB
    cosmos_client = get_cosmos_client()
    try:
        await cosmos_client.initialize()
        logger.info("CosmosDB initialized")
    except Exception as e:
        logger.warning("CosmosDB failed (degraded mode): %s", e)

    # 3. Build Guardrail Agent
    guardrail_graph = build_guardrail_graph()
    app.state.guardrail_agent = guardrail_graph
    logger.info("Guardrail Agent ready")

    # 4. Build Telegram Bot Application with handlers
    bot_app = await _build_bot_app(settings)

    # Inject services into bot_data for handlers to use
    from src.api.application.services.user_service import UserService
    from src.api.application.services.session_service import SessionService
    from src.api.application.services.question_service import QuestionService
    from src.api.application.services.progress_service import ProgressService
    from src.api.application.services.feedback_service import FeedbackService
    from src.api.domain.repositories.user_repository import UserRepository
    from src.api.domain.repositories.question_repository import QuestionRepository
    from src.api.domain.repositories.answer_repository import AnswerRepository
    from src.api.domain.repositories.feedback_repository import FeedbackRepository
    from src.api.domain.repositories.session_repository import SessionRepository

    # Create repositories (use cosmos containers if available)
    try:
        user_repo = UserRepository(cosmos_client.users)
        question_repo = QuestionRepository(cosmos_client.questions)
        answer_repo = AnswerRepository(cosmos_client.user_questions)
        feedback_repo = FeedbackRepository(cosmos_client.question_feedback)
        # Session repo uses user_questions container for now
        session_repo = SessionRepository(cosmos_client.user_questions)

        bot_app.bot_data["user_service"] = UserService(user_repository=user_repo)
        bot_app.bot_data["question_service"] = QuestionService(
            question_repository=question_repo, answer_repository=answer_repo
        )
        bot_app.bot_data["session_service"] = SessionService(
            session_repository=session_repo,
            question_repository=question_repo,
            answer_repository=answer_repo,
        )
        bot_app.bot_data["progress_service"] = ProgressService(
            answer_repository=answer_repo, question_repository=question_repo
        )
        bot_app.bot_data["feedback_service"] = FeedbackService(
            feedback_repository=feedback_repo
        )
        bot_app.bot_data["poll_to_question"] = {}
        bot_app.bot_data["poll_to_user"] = {}
        logger.info("Services wired with CosmosDB repositories")
    except Exception as e:
        logger.warning("Could not wire services (CosmosDB unavailable): %s", e)
        # Handlers will fail gracefully if services aren't in bot_data

    app.state.bot_app = bot_app
    logger.info("Telegram Bot Application ready")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await bot_app.shutdown()
    await cosmos_client.close()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="Certification Genie",
        description="Multi-agent Telegram bot for AI-103 certification preparation",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(webhook_router)
    return app


app = create_app()
