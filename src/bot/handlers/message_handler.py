"""Free-text message handler for the Certification Genie Telegram bot.

Handles:
- Q&A mode queries (routes to QA Agent when in free_qa session)
- "why"/"explain" triggers after incorrect answers (routes to Explainer Agent)
- Unrecognized messages outside of active sessions

Services are injected via context.bot_data.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.keyboards.main_menu import build_main_menu

logger = logging.getLogger(__name__)

# Trigger words for detailed explanation requests
_EXPLANATION_TRIGGERS = {"why", "explain"}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming free-text messages.

    Routes based on the user's current session state:
    - free_qa session: forwards to QA Agent for RAG-based answers
    - training session with recent incorrect answer: triggers explanation
    - No session: prompts user to start one
    """
    if update.message is None or update.message.text is None:
        return

    text = update.message.text.strip()
    if not text:
        return

    user_service = context.bot_data["user_service"]
    session_service = context.bot_data["session_service"]

    telegram_id = update.effective_user.id
    user = await user_service.register_or_get_user(telegram_id)

    # Check current session
    session = await session_service.get_current_session(user.id)

    if session is None:
        # No active session — guide user to start one
        await update.message.reply_text(
            "No active session. Choose a mode to get started:",
            reply_markup=build_main_menu(),
        )
        return

    if session.session_type == "free_qa":
        await _handle_free_qa_message(update, context, user.id, text)
    elif session.session_type == "training":
        await _handle_training_message(update, context, user.id, text)
    elif session.session_type == "simulation":
        await update.message.reply_text(
            "During simulation, only poll answers and /end\\_simulation are accepted.",
            parse_mode="Markdown",
        )


async def _handle_free_qa_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str, text: str
) -> None:
    """Handle a message in free Q&A mode.

    Passes the user's question to the QA Agent (via Guardrail Agent first).
    The QA Agent searches Azure documentation and returns a grounded answer.
    """
    # In a full implementation, this would:
    # 1. Pass through Guardrail Agent for safety screening
    # 2. Forward to QA Agent for RAG-based answer
    # For now, delegate to the QA agent if available in bot_data

    guardrail_agent = context.bot_data.get("guardrail_agent")
    qa_agent = context.bot_data.get("qa_agent")

    # Step 1: Guardrail check
    if guardrail_agent is not None:
        guardrail_result = await guardrail_agent.invoke({"user_message": text})
        if guardrail_result.get("output_message") is not None:
            # Input was blocked
            await update.message.reply_text(guardrail_result["output_message"])
            return

    # Step 2: QA Agent processing
    if qa_agent is not None:
        try:
            qa_result = await qa_agent.invoke({"user_query": text})
            answer = qa_result.get("answer", "")
            sources = qa_result.get("sources", [])

            response_parts = [answer]
            if sources:
                response_parts.append("\n\n📎 *Sources:*")
                for source in sources[:3]:
                    response_parts.append(f"• {source}")

            await update.message.reply_text(
                "\n".join(response_parts),
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.error("QA Agent error: %s", exc)
            await update.message.reply_text(
                "I'm having trouble searching documentation right now. "
                "Please try again in a moment."
            )
    else:
        # Fallback when QA agent is not wired yet
        await update.message.reply_text(
            "💬 I received your question. The QA system is being set up.\n"
            "Use /exit to return to the main menu."
        )


async def _handle_training_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str, text: str
) -> None:
    """Handle a message during a training session.

    Checks for "why"/"explain" triggers to provide detailed explanations.
    """
    lower_text = text.lower().strip()

    # Check if this is an explanation request
    if lower_text in _EXPLANATION_TRIGGERS:
        await _provide_detailed_explanation(update, context, user_id)
        return

    # Other text during training is not expected
    await update.message.reply_text(
        "Answer the question above using the poll, "
        'or type "why" / "explain" for a detailed explanation of the last answer.'
    )


async def _provide_detailed_explanation(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str
) -> None:
    """Provide a detailed explanation for the last incorrect answer.

    Delegates to the Explainer Agent if available, which searches
    Azure documentation for additional context.
    """
    user_last_incorrect = context.bot_data.get("user_last_incorrect", {})
    question_id = user_last_incorrect.get(user_id)

    if question_id is None:
        await update.message.reply_text(
            "No recent incorrect answer to explain. "
            "Answer a question first, then ask for an explanation."
        )
        return

    question_service = context.bot_data["question_service"]
    question_doc = await question_service._question_repository.get_by_id(
        question_id, partition_key="AI-103"
    )

    if question_doc is None:
        await update.message.reply_text("Could not find the question to explain.")
        return

    # Try the Explainer Agent if available
    explainer_agent = context.bot_data.get("explainer_agent")
    guardrail_agent = context.bot_data.get("guardrail_agent")

    if explainer_agent is not None:
        try:
            explainer_input = {
                "question_text": question_doc["text"],
                "options": question_doc["options"],
                "correct_answer_index": question_doc["correct_answer_index"],
                "user_selected_index": -1,  # Not tracked at this level
                "short_explanation": question_doc.get("short_explanation", ""),
                "detailed_explanation": question_doc.get("detailed_explanation", ""),
                "needs_enrichment": True,
            }

            result = await explainer_agent.invoke(explainer_input)
            explanation = result.get(
                "enriched_explanation",
                result.get("detailed_explanation", question_doc.get("detailed_explanation", "")),
            )
        except Exception as exc:
            logger.error("Explainer Agent error: %s", exc)
            explanation = question_doc.get("detailed_explanation", "")
    else:
        # Fallback to stored detailed explanation
        explanation = question_doc.get("detailed_explanation", "")

    from src.bot.formatters.explanation_formatter import format_explanation

    formatted = format_explanation(
        explanation=explanation,
        question_text=question_doc["text"],
        correct_option=question_doc["options"][question_doc["correct_answer_index"]],
    )

    await update.message.reply_text(formatted, parse_mode="Markdown")
