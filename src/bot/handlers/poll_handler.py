"""Poll answer handler for the Certification Genie Telegram bot.

Poll-to-question mappings are persisted in CosmosDB so they survive
container restarts and scale-to-zero events.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.api.domain.models.question import Question
from src.bot.formatters.explanation_formatter import format_explanation
from src.bot.formatters.question_formatter import format_question_as_poll
from src.bot.keyboards.feedback_buttons import build_feedback_buttons

logger = logging.getLogger(__name__)


async def save_poll_mapping(context, poll_id: str, question_id: str, user_id: str) -> None:
    """Persist poll → question/user mapping to CosmosDB + in-memory cache."""
    context.bot_data.setdefault("poll_to_question", {})[poll_id] = question_id
    context.bot_data.setdefault("poll_to_user", {})[poll_id] = user_id
    try:
        from src.api.infrastructure.cosmos_client import get_cosmos_client
        cosmos = get_cosmos_client()
        await cosmos.user_questions.upsert_item({
            "id": f"poll:{poll_id}",
            "user_id": user_id,
            "question_id": question_id,
            "type": "poll_mapping",
        })
    except Exception as e:
        logger.debug("Could not persist poll mapping: %s", e)


async def get_poll_mapping(context, poll_id: str) -> tuple[str | None, str | None]:
    """Retrieve poll mapping — memory first, then CosmosDB."""
    question_id = context.bot_data.get("poll_to_question", {}).get(poll_id)
    user_id = context.bot_data.get("poll_to_user", {}).get(poll_id)
    if question_id and user_id:
        return question_id, user_id
    try:
        from src.api.infrastructure.cosmos_client import get_cosmos_client
        cosmos = get_cosmos_client()
        doc = await cosmos.user_questions.read_item(
            item=f"poll:{poll_id}", partition_key=f"poll:{poll_id}"
        )
        question_id = doc.get("question_id")
        user_id = doc.get("user_id")
        if question_id and user_id:
            context.bot_data.setdefault("poll_to_question", {})[poll_id] = question_id
            context.bot_data.setdefault("poll_to_user", {})[poll_id] = user_id
        return question_id, user_id
    except Exception:
        return None, None


async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a user's poll answer."""
    poll_answer = update.poll_answer
    if poll_answer is None:
        return

    poll_id = poll_answer.poll_id
    selected_option = poll_answer.option_ids[0] if poll_answer.option_ids else 0

    question_id, user_id = await get_poll_mapping(context, poll_id)
    if question_id is None or user_id is None:
        logger.warning("Received poll answer for unknown poll: %s", poll_id)
        return

    session_service = context.bot_data["session_service"]
    question_service = context.bot_data["question_service"]

    try:
        answer_record = await session_service.record_answer(
            user_id=user_id,
            question_id=question_id,
            selected_answer=selected_option,
        )
    except Exception as exc:
        logger.error("Failed to record answer: %s", exc)
        return

    session = await session_service.get_current_session(user_id)
    if session is None:
        return

    chat_id = poll_answer.user.id

    if session.session_type == "training":
        await _handle_training_answer(
            context, chat_id, user_id, question_id,
            answer_record, session, question_service,
        )
    elif session.session_type == "simulation":
        await _handle_simulation_answer(
            context, chat_id, user_id, session, question_service,
        )


async def _handle_training_answer(context, chat_id, user_id, question_id, answer_record, session, question_service):
    """Training mode: show feedback, then next question."""
    question_doc = await question_service._question_repository.get_by_id(question_id, partition_key="AI-103")

    if answer_record.is_correct:
        await context.bot.send_message(chat_id=chat_id, text="✅ Correct!", reply_markup=build_feedback_buttons(question_id))
        await _send_next_training_question(context, chat_id, user_id, session, question_service)
    else:
        short_explanation = question_doc.get("short_explanation", "") if question_doc else ""
        correct_index = question_doc.get("correct_answer_index", 0) if question_doc else 0
        options = question_doc.get("options", []) if question_doc else []
        correct_option = options[correct_index] if options else ""
        explanation_text = format_explanation(explanation=short_explanation, correct_option=correct_option)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Incorrect.\n\n{explanation_text}\n\nType \"why\" for a detailed explanation.",
            reply_markup=build_feedback_buttons(question_id),
        )
        context.bot_data.setdefault("user_last_incorrect", {})[user_id] = question_id
        # Send next question after incorrect too
        await _send_next_training_question(context, chat_id, user_id, session, question_service)


async def _handle_simulation_answer(context, chat_id, user_id, session, question_service):
    """Simulation mode: silently advance to next question."""
    session_service = context.bot_data["session_service"]
    current_index = session.current_question_index

    if current_index >= len(session.questions_served):
        summary = await session_service.end_session(user_id)
        if summary:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📝 Simulation complete!\nScore: {summary['score']}/{summary['total']} ({summary['percentage']:.1f}%)",
            )
        return

    next_question_id = session.questions_served[current_index]
    question_doc = await question_service._question_repository.get_by_id(next_question_id, partition_key="AI-103")
    if question_doc:
        question = Question(**question_doc)
        poll_params = format_question_as_poll(question)
        sent_poll = await context.bot.send_poll(
            chat_id=chat_id, question=poll_params.question, options=poll_params.options,
            type=poll_params.type, correct_option_id=poll_params.correct_option_id, is_anonymous=poll_params.is_anonymous,
        )
        await save_poll_mapping(context, sent_poll.poll.id, next_question_id, user_id)


async def _send_next_training_question(context, chat_id, user_id, session, question_service):
    """Send next unanswered question, or generate a new one if exhausted."""
    import random

    unanswered = await question_service.get_unanswered_questions(user_id, "AI-103")

    if not unanswered:
        await context.bot.send_message(chat_id=chat_id, text="🧠 All questions answered! Generating a new one...")
        try:
            new_q = await _generate_new_question(question_service)
            if new_q:
                next_question_doc = new_q
                next_question_id = new_q["id"]
            else:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Could not generate a question. Try /train later.")
                return
        except Exception as e:
            logger.error("Generation failed: %s", e)
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Generation failed. Try /train later.")
            return
    else:
        next_question_doc = random.choice(unanswered)
        next_question_id = next_question_doc["id"]

    question = Question(**next_question_doc)
    poll_params = format_question_as_poll(question)
    sent_poll = await context.bot.send_poll(
        chat_id=chat_id, question=poll_params.question, options=poll_params.options,
        type=poll_params.type, correct_option_id=poll_params.correct_option_id, is_anonymous=poll_params.is_anonymous,
    )
    await save_poll_mapping(context, sent_poll.poll.id, next_question_id, user_id)


async def _generate_new_question(question_service) -> dict | None:
    """Generate a new question via Generator Agent, validate, persist."""
    import random
    import uuid
    from datetime import datetime, timezone
    from src.ai.agents.generator_agent.graph import build_generator_graph
    from src.api.domain.enums.domain_type import DomainType

    domain = random.choice(list(DomainType))
    existing = await question_service._question_repository.get_active_by_certification("AI-103")
    examples = [q for q in existing if q.get("domain") == domain.value][:3]

    graph = build_generator_graph()
    for attempt in range(2):
        result = await graph.ainvoke({
            "certification": "AI-103",
            "target_domain": domain.value,
            "example_questions": examples,
            "feedback_context": None,
            "generated_question": None,
            "is_valid": False,
            "validation_errors": [],
        })
        if result.get("is_valid") and result.get("generated_question"):
            break
        logger.warning("Generator attempt %d failed: %s", attempt + 1, result.get("validation_errors"))
    else:
        return None

    question_data = result["generated_question"]
    question_data["id"] = str(uuid.uuid4())
    question_data["created_at"] = datetime.now(timezone.utc).isoformat()
    question_data["quality_score"] = 1.0
    question_data["is_active"] = True
    question_data["generated_by"] = "generator_agent"
    question_data["domain"] = domain.value
    question_data["certification"] = "AI-103"

    await question_service._question_repository.create(question_data)
    logger.info("Generated new question: %s (domain=%s)", question_data["id"][:8], domain.value)
    return question_data
