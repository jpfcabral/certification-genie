"""Explain node for the Explainer Agent.

Generates a structured explanation of why the correct answer is right
and why each alternative is wrong. Respects the 4096 character limit.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.ai.agents.explainer_agent.prompts.explainer_prompt import (
    EXPLAINER_SYSTEM_PROMPT,
    MAX_EXPLANATION_LENGTH,
)
from src.ai.agents.explainer_agent.state import ExplainerState


def _build_explain_user_prompt(state: ExplainerState) -> str:
    """Build the user prompt with question context."""
    options_text = "\n".join(
        f"  {chr(65 + i)}. {opt}" for i, opt in enumerate(state["options"])
    )
    correct_letter = chr(65 + state["correct_answer_index"])
    selected_letter = chr(65 + state["user_selected_index"])

    return (
        f"Question: {state['question_text']}\n\n"
        f"Options:\n{options_text}\n\n"
        f"Correct Answer: {correct_letter}. "
        f"{state['options'][state['correct_answer_index']]}\n"
        f"Student Selected: {selected_letter}. "
        f"{state['options'][state['user_selected_index']]}\n\n"
        f"Short explanation provided: {state['short_explanation']}\n\n"
        "Please provide a detailed explanation of why the correct answer "
        "is right and why each other option is wrong."
    )


def _truncate_explanation(text: str, max_length: int = MAX_EXPLANATION_LENGTH) -> str:
    """Truncate explanation to fit within character limit while preserving readability."""
    if len(text) <= max_length:
        return text
    # Truncate at last complete sentence before limit
    truncated = text[: max_length - 3]
    last_period = truncated.rfind(".")
    if last_period > max_length // 2:
        return truncated[: last_period + 1]
    return truncated + "..."


async def explain_node(state: ExplainerState) -> dict:
    """Generate a structured explanation for an incorrect answer.

    Uses the LLM to explain why the correct answer is right and why
    each alternative is wrong. The output respects the 4096 char limit.

    Args:
        state: Current explainer state with question context.

    Returns:
        Updated state with detailed_explanation populated.
    """
    from src.api.infrastructure.config import get_settings
    llm = ChatOpenAI(model=get_settings().OPENAI_MODEL, temperature=0.3)

    messages = [
        SystemMessage(content=EXPLAINER_SYSTEM_PROMPT),
        HumanMessage(content=_build_explain_user_prompt(state)),
    ]

    response = await llm.ainvoke(messages)
    explanation = _truncate_explanation(response.content)

    return {
        "detailed_explanation": explanation,
        "needs_enrichment": state.get("needs_enrichment", False),
    }
