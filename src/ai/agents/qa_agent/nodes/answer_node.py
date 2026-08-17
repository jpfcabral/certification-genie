"""Answer node for the QA Agent.

Synthesizes a final answer with citations from the search results
retrieved by the search node.
"""

from langchain_openai import ChatOpenAI

from src.ai.agents.qa_agent.prompts.qa_prompt import (
    NO_RESULTS_RESPONSE,
    OUT_OF_SCOPE_RESPONSE,
    QA_SYSTEM_PROMPT,
    QA_USER_PROMPT,
    SCOPE_CHECK_PROMPT,
)
from src.ai.agents.qa_agent.state import QAState
from src.api.infrastructure.config import get_settings


async def answer_node(state: QAState) -> dict:
    """Synthesize an answer with citations from search results.

    Uses the LLM to generate a comprehensive answer based on the retrieved
    documentation, including proper source citations. Handles scope checking
    and no-results scenarios gracefully.

    Args:
        state: Current QA agent state containing user_query, search_results,
            and is_in_scope flag.

    Returns:
        Dict with the final answer text and list of source references.
    """
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.3,
    )

    # Check scope if not already determined
    if not state.get("is_in_scope", True):
        return {
            "answer": OUT_OF_SCOPE_RESPONSE,
            "sources": [],
            "is_in_scope": False,
        }

    # If no search results and answer already set (search failure), pass through
    if not state.get("search_results") and state.get("answer"):
        return {}

    # Verify scope using LLM
    is_in_scope = await _check_scope(llm, state["user_query"])
    if not is_in_scope:
        return {
            "answer": OUT_OF_SCOPE_RESPONSE,
            "sources": [],
            "is_in_scope": False,
        }

    # Handle no search results
    if not state.get("search_results"):
        return {
            "answer": NO_RESULTS_RESPONSE,
            "sources": [],
            "is_in_scope": True,
        }

    # Format search results for the prompt
    formatted_results = _format_search_results(state["search_results"])

    # Generate answer with citations
    system_message = QA_SYSTEM_PROMPT.format(search_results=formatted_results)
    user_message = QA_USER_PROMPT.format(user_query=state["user_query"])

    response = await llm.ainvoke(
        [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]
    )

    # Extract sources from search results
    sources = [
        r["source"]
        for r in state.get("search_results", [])
        if r.get("source")
    ]

    return {
        "answer": response.content,
        "sources": sources,
        "is_in_scope": True,
    }


async def _check_scope(llm: ChatOpenAI, user_query: str) -> bool:
    """Check if the user's query is within the AI-103 certification scope.

    Args:
        llm: The language model to use for classification.
        user_query: The user's question.

    Returns:
        True if the query is in scope, False otherwise.
    """
    try:
        prompt = SCOPE_CHECK_PROMPT.format(user_query=user_query)
        response = await llm.ainvoke(prompt)
        return "in_scope" in response.content.lower()
    except Exception:
        # Fail open for scope check — allow the question through
        return True


def _format_search_results(results: list[dict]) -> str:
    """Format search results into a readable string for the LLM prompt.

    Args:
        results: List of search result dicts with content, source, and title.

    Returns:
        Formatted string containing all search results.
    """
    formatted_parts = []
    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        source = result.get("source", "Unknown source")
        content = result.get("content", "")
        formatted_parts.append(
            f"[{i}] {title}\n"
            f"    Source: {source}\n"
            f"    Content: {content}\n"
        )
    return "\n".join(formatted_parts)
