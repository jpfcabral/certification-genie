"""Enrich node for the Explainer Agent.

Fetches additional documentation context when a user asks "why" or
"explain", providing a deeper explanation grounded in Azure documentation.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.ai.agents.explainer_agent.prompts.explainer_prompt import (
    ENRICHMENT_SYSTEM_PROMPT,
    MAX_EXPLANATION_LENGTH,
)
from src.ai.agents.explainer_agent.state import ExplainerState
from src.ai.agents.explainer_agent.tools.documentation_tool import (
    search_azure_documentation,
)


def _build_enrich_user_prompt(state: ExplainerState, doc_context: str) -> str:
    """Build the user prompt for enrichment with documentation context."""
    options_text = "\n".join(
        f"  {chr(65 + i)}. {opt}" for i, opt in enumerate(state["options"])
    )
    correct_letter = chr(65 + state["correct_answer_index"])

    return (
        f"Question: {state['question_text']}\n\n"
        f"Options:\n{options_text}\n\n"
        f"Correct Answer: {correct_letter}. "
        f"{state['options'][state['correct_answer_index']]}\n\n"
        f"Previous explanation: {state['detailed_explanation']}\n\n"
        f"Documentation context:\n{doc_context}\n\n"
        "The student wants a deeper explanation. Use the documentation "
        "context to provide additional detail and cite sources."
    )


def _truncate_explanation(text: str, max_length: int = MAX_EXPLANATION_LENGTH) -> str:
    """Truncate explanation to fit within character limit while preserving readability."""
    if len(text) <= max_length:
        return text
    truncated = text[: max_length - 3]
    last_period = truncated.rfind(".")
    if last_period > max_length // 2:
        return truncated[: last_period + 1]
    return truncated + "..."


async def enrich_node(state: ExplainerState) -> dict:
    """Fetch documentation and provide an enriched explanation.

    Searches Azure documentation for additional context related to the
    question topic, then uses the LLM to synthesize a deeper explanation
    with citations.

    Args:
        state: Current explainer state with question and prior explanation.

    Returns:
        Updated state with enriched_explanation and documentation_sources.
    """
    # Search documentation for relevant context
    search_query = f"{state['question_text']} {state['options'][state['correct_answer_index']]}"
    doc_context = search_azure_documentation.invoke({"query": search_query})

    # Extract sources from the documentation context
    sources: list[str] = []
    if "https://" in doc_context:
        for line in doc_context.split("\n"):
            if "https://" in line:
                # Extract URL from the line
                start = line.find("https://")
                end = len(line)
                for char_idx in range(start, len(line)):
                    if line[char_idx] in (" ", "\n", "\t"):
                        end = char_idx
                        break
                sources.append(line[start:end])

    from src.api.infrastructure.config import get_settings
    llm = ChatOpenAI(model=get_settings().OPENAI_MODEL, temperature=0.3)

    messages = [
        SystemMessage(content=ENRICHMENT_SYSTEM_PROMPT),
        HumanMessage(content=_build_enrich_user_prompt(state, doc_context)),
    ]

    response = await llm.ainvoke(messages)
    enriched = _truncate_explanation(response.content)

    return {
        "enriched_explanation": enriched,
        "documentation_sources": sources,
    }
