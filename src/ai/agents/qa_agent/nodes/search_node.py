"""Search node for the QA Agent.

Searches Azure documentation via LLM-powered web search to find
relevant content for answering the user's question. Prioritizes
results from learn.microsoft.com.
"""

from src.ai.agents.qa_agent.prompts.qa_prompt import SEARCH_UNAVAILABLE_RESPONSE
from src.ai.agents.qa_agent.state import QAState
from src.ai.agents.qa_agent.tools.web_search_tool import (
    prioritize_microsoft_sources,
    web_search,
)
from src.api.infrastructure.config import get_settings


async def search_node(state: QAState) -> dict:
    """Search Azure documentation for information relevant to the user's query.

    Uses LLM-powered web search to find documentation excerpts from
    learn.microsoft.com. Results are prioritized by source authority.

    Args:
        state: Current QA agent state containing user_query and is_in_scope.

    Returns:
        Dict with updated search_results and sources.
    """
    # If query was already classified as out of scope, skip search
    if not state.get("is_in_scope", True):
        return {
            "search_results": [],
            "sources": [],
        }

    settings = get_settings()

    # Search via LLM-powered web search
    results = await web_search(
        query=state["user_query"],
        api_key=settings.OPENAI_API_KEY,
    )

    # Check if search failed
    if not results:
        return {
            "search_results": [],
            "answer": SEARCH_UNAVAILABLE_RESPONSE,
            "sources": [],
        }

    # Prioritize Microsoft documentation sources
    prioritized_results = prioritize_microsoft_sources(results)

    # Extract source URLs
    sources = [r["source"] for r in prioritized_results if r.get("source")]

    return {
        "search_results": prioritized_results,
        "sources": sources,
    }
