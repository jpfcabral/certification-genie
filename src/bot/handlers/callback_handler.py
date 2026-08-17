"""Callback query handler for InlineKeyboard interactions.

Processes callbacks from:
- Main menu navigation (menu:training, menu:simulation, menu:free_qa)
- Feedback buttons (feedback:positive, feedback:negative, feedback:flag)
- Flag subcategory selection (flag:<type>:<question_id>)
- Flashcard reveal (flashcard:reveal:<domain>)
- Domain selection (domain:<domain_name>)

Services are injected via context.bot_data.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.api.application.services.session_service import ActiveSessionExistsError
from src.bot.keyboards.feedback_buttons import build_flag_subcategories
from src.bot.keyboards.main_menu import build_main_menu

logger = logging.getLogger(__name__)


async def handle_callback_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Route callback queries to appropriate sub-handlers.

    Parses the callback_data prefix and delegates to the matching handler.
    """
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    data = query.data or ""

    if data.startswith("menu:"):
        await _handle_menu_callback(update, context, data)
    elif data.startswith("feedback:"):
        await _handle_feedback_callback(update, context, data)
    elif data.startswith("flag:"):
        await _handle_flag_callback(update, context, data)
    elif data.startswith("flashcard:"):
        await _handle_flashcard_callback(update, context, data)
    elif data.startswith("domain:"):
        await _handle_domain_callback(update, context, data)
    else:
        logger.warning("Unknown callback data: %s", data)


async def _handle_menu_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle main menu button presses.

    Routes to training, simulation, or free Q&A based on selection.
    """
    query = update.callback_query
    action = data.removeprefix("menu:")

    user_service = context.bot_data["user_service"]
    session_service = context.bot_data["session_service"]

    telegram_id = update.effective_user.id
    user = await user_service.register_or_get_user(telegram_id)

    if action == "training":
        try:
            session = await session_service.start_training(user.id)
        except ActiveSessionExistsError:
            await query.edit_message_text(
                "You already have an active session. "
                "Use /exit to end it before starting a new one."
            )
            return

        if not session.questions_served:
            await query.edit_message_text(
                "No questions available yet. New questions will be generated soon!"
            )
            return

        await query.edit_message_text("📚 Training mode started! Here's your first question:")

        # Send the first question as a poll
        question_service = context.bot_data["question_service"]
        question_id = session.questions_served[0]
        question_doc = await question_service._question_repository.get_by_id(
            question_id, partition_key="AI-103"
        )

        if question_doc:
            from src.api.domain.models.question import Question
            from src.bot.formatters.question_formatter import format_question_as_poll

            question = Question(**question_doc)
            poll_params = format_question_as_poll(question)

            sent_poll = await context.bot.send_poll(
                chat_id=query.message.chat_id,
                question=poll_params.question,
                options=poll_params.options,
                type=poll_params.type,
                correct_option_id=poll_params.correct_option_id,
                is_anonymous=poll_params.is_anonymous,
            )

            from src.bot.handlers.poll_handler import save_poll_mapping
            await save_poll_mapping(context, sent_poll.poll.id, question_id, user.id)

    elif action == "free_qa":
        try:
            await session_service.start_free_qa(user.id)
        except ActiveSessionExistsError:
            await query.edit_message_text(
                "You already have an active session. "
                "Use /exit to end it before starting a new one."
            )
            return

        await query.edit_message_text(
            "💬 Free Q&A mode activated!\n\n"
            "Ask me anything about Azure AI Services and AI-103 topics.\n"
            "Use /exit to return to the main menu."
        )


async def _handle_feedback_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle feedback button presses (thumbs up, thumbs down, flag).

    callback_data format: feedback:<type>:<question_id>
    """
    query = update.callback_query
    parts = data.split(":")

    if len(parts) < 3:
        logger.warning("Invalid feedback callback data: %s", data)
        return

    feedback_type = parts[1]  # positive, negative, flag
    question_id = parts[2]

    user_service = context.bot_data["user_service"]
    feedback_service = context.bot_data["feedback_service"]

    telegram_id = update.effective_user.id
    user = await user_service.register_or_get_user(telegram_id)

    if feedback_type == "flag":
        # Show flag subcategories
        await query.edit_message_reply_markup(
            reply_markup=build_flag_subcategories(question_id)
        )
        return

    if feedback_type in ("positive", "negative"):
        await feedback_service.record_feedback(
            user_id=user.id,
            question_id=question_id,
            rating=feedback_type,
        )

        emoji = "👍" if feedback_type == "positive" else "👎"
        await query.edit_message_text(
            f"{emoji} Thanks for your feedback!"
        )


async def _handle_flag_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle flag subcategory selection.

    callback_data format: flag:<flag_type>:<question_id>
    """
    query = update.callback_query
    parts = data.split(":")

    if len(parts) < 3:
        logger.warning("Invalid flag callback data: %s", data)
        return

    flag_type = parts[1]  # incorrect_answer, ambiguous, too_easy, too_hard, off_topic
    question_id = parts[2]

    user_service = context.bot_data["user_service"]
    feedback_service = context.bot_data["feedback_service"]

    telegram_id = update.effective_user.id
    user = await user_service.register_or_get_user(telegram_id)

    await feedback_service.record_feedback(
        user_id=user.id,
        question_id=question_id,
        rating="negative",
        flag_type=flag_type,
    )

    await query.edit_message_text(
        "🚩 Question flagged. Thanks for helping us improve!"
    )


async def _handle_flashcard_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle flashcard reveal button.

    callback_data format: flashcard:reveal:<domain_name>
    """
    query = update.callback_query
    parts = data.split(":")

    if len(parts) < 3:
        logger.warning("Invalid flashcard callback data: %s", data)
        return

    domain_name = parts[2]

    from src.api.domain.enums.domain_type import DomainType

    try:
        domain = DomainType[domain_name]
    except KeyError:
        await query.edit_message_text("Unknown domain.")
        return

    # Provide a concept explanation for the selected domain
    # In a full implementation, this would query a concept database or
    # the Explainer Agent. For now, provide domain description.
    await query.edit_message_text(
        f"🃏 *Flashcard — {domain.value}*\n\n"
        f"This domain covers {domain.value.lower()} topics in the AI-103 exam "
        f"and accounts for {domain.weight * 100:.0f}% of the exam questions.\n\n"
        f"Use /flashcard for another card, or /train to practice questions.",
        parse_mode="Markdown",
    )


async def _handle_domain_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, data: str
) -> None:
    """Handle domain selection from the domain keyboard.

    callback_data format: domain:<DOMAIN_NAME>
    """
    query = update.callback_query
    domain_name = data.removeprefix("domain:")

    from src.api.domain.enums.domain_type import DomainType

    try:
        domain = DomainType[domain_name]
    except KeyError:
        await query.edit_message_text("Unknown domain selected.")
        return

    await query.edit_message_text(
        f"Selected domain: *{domain.value}* ({domain.weight * 100:.0f}% of exam)\n\n"
        f"Use /train to start practicing questions from this domain.",
        parse_mode="Markdown",
    )
