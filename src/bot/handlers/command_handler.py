"""Command handlers for the Certification Genie Telegram bot.

Handles /start, /train, /simulate, /ask, /progress, /exit,
/flashcard, /domains, /weak_areas, and /reminders commands.

Services are injected via context.bot_data, keyed by service name:
- "user_service": UserService
- "session_service": SessionService
- "progress_service": ProgressService
- "question_service": QuestionService
- "feedback_service": FeedbackService
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.api.application.services.session_service import (
    ActiveSessionExistsError,
    NoActiveSessionError,
)
from src.api.domain.enums.domain_type import DomainType, get_domain_weights
from src.bot.formatters.progress_formatter import format_progress_summary
from src.bot.formatters.question_formatter import format_question_as_poll
from src.bot.keyboards.feedback_buttons import build_feedback_buttons
from src.bot.keyboards.main_menu import build_main_menu

logger = logging.getLogger(__name__)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command — register user and show main menu.

    Registers the user if not already registered (idempotent), then
    displays the main menu with Training, Simulation, and Free Q&A.
    """
    user_service = context.bot_data["user_service"]
    telegram_id = update.effective_user.id

    await user_service.register_or_get_user(telegram_id)

    await update.message.reply_text(
        "Welcome to Certification Genie! 🧞‍♂️\n\n"
        "I'll help you prepare for Azure AI-103 certification.\n"
        "Choose a study mode below:",
        reply_markup=build_main_menu(),
    )


async def handle_train(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /train command — start a training session.

    Creates a training session and sends the first question as a poll.
    """
    user_service = context.bot_data["user_service"]
    session_service = context.bot_data["session_service"]
    question_service = context.bot_data["question_service"]

    telegram_id = update.effective_user.id
    user = await user_service.register_or_get_user(telegram_id)

    try:
        session = await session_service.start_training(user.id)
    except ActiveSessionExistsError:
        await update.message.reply_text(
            "You already have an active session. "
            "Use /exit to end it before starting a new one."
        )
        return

    if not session.questions_served:
        await update.message.reply_text(
            "No questions available yet. New questions will be generated soon!"
        )
        return

    # Fetch and send the first question
    question_id = session.questions_served[0]
    question_doc = await question_service._question_repository.get_by_id(
        question_id, partition_key="AI-103"
    )

    if question_doc is None:
        await update.message.reply_text("Could not load question. Please try again.")
        return

    from src.api.domain.models.question import Question

    question = Question(**question_doc)
    poll_params = format_question_as_poll(question)

    sent_poll = await update.message.reply_poll(
        question=poll_params.question,
        options=poll_params.options,
        type=poll_params.type,
        correct_option_id=poll_params.correct_option_id,
        is_anonymous=poll_params.is_anonymous,
    )

    # Store poll-to-question mapping (persisted to CosmosDB)
    from src.bot.handlers.poll_handler import save_poll_mapping
    await save_poll_mapping(context, sent_poll.poll.id, question_id, user.id)


async def handle_simulate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /simulate command — start a simulation session.

    Creates a simulation session with 20 questions distributed across
    domains and sends the first question.
    """
    user_service = context.bot_data["user_service"]
    session_service = context.bot_data["session_service"]
    question_service = context.bot_data["question_service"]

    telegram_id = update.effective_user.id
    user = await user_service.register_or_get_user(telegram_id)

    try:
        session = await session_service.start_simulation(user.id)
    except ActiveSessionExistsError:
        await update.message.reply_text(
            "You already have an active session. "
            "Use /exit to end it before starting a new one."
        )
        return

    total = session.total_questions or len(session.questions_served)
    await update.message.reply_text(
        f"📝 *Simulation started!*\n\n"
        f"You'll answer {total} questions across all AI-103 domains.\n"
        f"No explanations will be shown until the end.\n\n"
        f"Use /end\\_simulation to exit early.",
        parse_mode="Markdown",
    )

    # Send first question
    if session.questions_served:
        question_id = session.questions_served[0]
        question_doc = await question_service._question_repository.get_by_id(
            question_id, partition_key="AI-103"
        )

        if question_doc:
            from src.api.domain.models.question import Question

            question = Question(**question_doc)
            poll_params = format_question_as_poll(question)

            sent_poll = await update.message.reply_poll(
                question=poll_params.question,
                options=poll_params.options,
                type=poll_params.type,
                correct_option_id=poll_params.correct_option_id,
                is_anonymous=poll_params.is_anonymous,
            )

            from src.bot.handlers.poll_handler import save_poll_mapping
            await save_poll_mapping(context, sent_poll.poll.id, question_id, user.id)


async def handle_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ask command — start free Q&A mode.

    Activates conversational mode where the user can ask free-form
    questions about Azure AI topics.
    """
    user_service = context.bot_data["user_service"]
    session_service = context.bot_data["session_service"]

    telegram_id = update.effective_user.id
    user = await user_service.register_or_get_user(telegram_id)

    try:
        await session_service.start_free_qa(user.id)
    except ActiveSessionExistsError:
        await update.message.reply_text(
            "You already have an active session. "
            "Use /exit to end it before starting a new one."
        )
        return

    await update.message.reply_text(
        "💬 *Free Q&A mode activated!*\n\n"
        "Ask me anything about Azure AI Services and AI-103 topics.\n"
        "I'll search official documentation to give you accurate answers.\n\n"
        "Use /exit to return to the main menu.",
        parse_mode="Markdown",
    )


async def handle_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /progress command — show user study progress.

    Displays total questions answered, overall percentage, and
    per-domain breakdown.
    """
    user_service = context.bot_data["user_service"]
    progress_service = context.bot_data["progress_service"]

    telegram_id = update.effective_user.id
    user = await user_service.register_or_get_user(telegram_id)

    progress = await progress_service.calculate_progress(user.id)

    if progress.get("insufficient_data"):
        await update.message.reply_text(
            f"📊 You've answered {progress['total_answered']} question(s) "
            f"({progress['correct_count']} correct).\n\n"
            "Answer at least 5 questions for a detailed analysis."
        )
        return

    summary = format_progress_summary(
        total_answered=progress["total_answered"],
        overall_percentage=progress["overall_percentage"],
        domain_breakdown=progress.get("per_domain", {}),
    )

    await update.message.reply_text(summary, parse_mode="Markdown")


async def handle_exit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /exit command — end the current session.

    Ends the active session and returns to the main menu.
    For simulation sessions, displays a summary.
    """
    user_service = context.bot_data["user_service"]
    session_service = context.bot_data["session_service"]

    telegram_id = update.effective_user.id
    user = await user_service.register_or_get_user(telegram_id)

    try:
        summary = await session_service.end_session(user.id)
    except NoActiveSessionError:
        await update.message.reply_text(
            "No active session to end. Use the menu to start one.",
            reply_markup=build_main_menu(),
        )
        return

    if summary:
        # Simulation summary with "Review mistakes" button
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        session_id = summary.get("session_id", "")
        review_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📖 Review mistakes",
                callback_data=f"review_mistakes:{session_id}",
            )]
        ])

        await update.message.reply_text(
            f"📝 *Simulation complete!*\n\n"
            f"Score: {summary['score']}/{summary['total']} "
            f"({summary['percentage']:.1f}%)\n\n"
            f"Use /weak\\_areas to see where to improve.",
            parse_mode="Markdown",
            reply_markup=review_keyboard,
        )
    else:
        await update.message.reply_text(
            "Session ended. Choose what to do next:",
            reply_markup=build_main_menu(),
        )


async def handle_flashcard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /flashcard command — present a random key concept.

    Serves a random concept from AI-103 domains as a short summary
    with a reveal button for detailed explanation.
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    # Flashcard concepts are served by domain; pick a random domain
    import random

    domain = random.choice(list(DomainType))

    await update.message.reply_text(
        f"🃏 *Flashcard — {domain.value}*\n\n"
        f"A key concept from this domain is ready for review.\n"
        f"Press the button below to reveal the explanation.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔍 Reveal explanation",
                callback_data=f"flashcard:reveal:{domain.name}",
            )]
        ]),
    )


async def handle_domains(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /domains command — display all domains with weights and performance.

    Shows AI-103 exam domains with their weight percentages and the
    user's current performance per domain.
    """
    user_service = context.bot_data["user_service"]
    progress_service = context.bot_data["progress_service"]

    telegram_id = update.effective_user.id
    user = await user_service.register_or_get_user(telegram_id)

    progress = await progress_service.calculate_progress(user.id)
    per_domain = progress.get("per_domain", {})
    weights = get_domain_weights()

    lines = ["📚 *AI-103 Exam Domains*\n"]

    for domain_type, weight in weights.items():
        domain_name = domain_type.value
        weight_pct = weight * 100
        user_pct = per_domain.get(domain_name)

        if user_pct is not None:
            lines.append(
                f"• *{domain_name}* (weight: {weight_pct:.0f}%)\n"
                f"  Your score: {user_pct:.1f}%"
            )
        else:
            lines.append(
                f"• *{domain_name}* (weight: {weight_pct:.0f}%)\n"
                f"  Your score: —"
            )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_weak_areas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /weak_areas command — show top 3 weakest domains.

    Analyzes user's answer records and suggests domains where the
    user needs the most improvement.
    """
    user_service = context.bot_data["user_service"]
    progress_service = context.bot_data["progress_service"]

    telegram_id = update.effective_user.id
    user = await user_service.register_or_get_user(telegram_id)

    weak_areas = await progress_service.get_weak_areas(user.id)

    if isinstance(weak_areas, dict) and weak_areas.get("insufficient_data"):
        await update.message.reply_text(
            f"📊 You've answered {weak_areas['total_answered']} question(s).\n\n"
            "Answer at least 5 questions for weak area analysis."
        )
        return

    lines = ["📉 *Your Top 3 Weak Areas*\n"]
    for i, area in enumerate(weak_areas, 1):
        lines.append(
            f"{i}. *{area['domain']}* — {area['percentage']:.1f}% correct\n"
            f"   Focus your study on this domain to improve."
        )

    lines.append("\nUse /train to practice questions from these areas.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reminders command — toggle daily study reminders.

    Usage: /reminders on or /reminders off
    """
    user_service = context.bot_data["user_service"]

    telegram_id = update.effective_user.id
    user = await user_service.register_or_get_user(telegram_id)

    # Parse the argument (on/off)
    args = context.args if context.args else []

    if not args or args[0].lower() not in ("on", "off"):
        status = "enabled" if user.reminders_enabled else "disabled"
        await update.message.reply_text(
            f"🔔 Daily reminders are currently *{status}*.\n\n"
            f"Usage: /reminders on or /reminders off",
            parse_mode="Markdown",
        )
        return

    enable = args[0].lower() == "on"

    # Update the user's reminder preference
    user_repo = user_service._repository
    user_doc = await user_repo.get_by_telegram_id(telegram_id)
    if user_doc:
        user_doc["reminders_enabled"] = enable
        await user_repo.update_user(user_doc)

    status = "enabled" if enable else "disabled"
    await update.message.reply_text(
        f"🔔 Daily reminders *{status}*.",
        parse_mode="Markdown",
    )
