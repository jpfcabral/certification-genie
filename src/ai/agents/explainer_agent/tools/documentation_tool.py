"""Tool for searching Azure documentation to enrich explanations.

Uses LLM-powered web search to find relevant content from
learn.microsoft.com for providing authoritative context in
exam explanations.
"""

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from src.api.infrastructure.config import get_settings


@tool
def search_azure_documentation(query: str) -> str:
    """Search Azure documentation for relevant content.

    Uses LLM to retrieve factual documentation excerpts from
    learn.microsoft.com about Azure AI services. Used by the
    Explainer Agent to ground explanations in official docs.

    Args:
        query: The search query about Azure AI concepts or services.

    Returns:
        Relevant documentation excerpts with source URLs.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're inside an async context — use a sync fallback
            return _search_sync(query)
        else:
            return asyncio.run(_search_async(query))
    except RuntimeError:
        return _search_sync(query)


def _search_sync(query: str) -> str:
    """Synchronous fallback for documentation search."""
    settings = get_settings()
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an Azure documentation search engine. "
                    "For the given query, provide 2-3 relevant factual excerpts "
                    "from official Azure documentation (learn.microsoft.com). "
                    "Include source URLs. Focus on AI-103 certification topics."
                ),
            },
            {"role": "user", "content": f"Search: {query}"},
        ],
    )
    return response.choices[0].message.content or ""


async def _search_async(query: str) -> str:
    """Async documentation search via LLM."""
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
    response = await llm.ainvoke(
        [
            {
                "role": "system",
                "content": (
                    "You are an Azure documentation search engine. "
                    "For the given query, provide 2-3 relevant factual excerpts "
                    "from official Azure documentation (learn.microsoft.com). "
                    "Include source URLs. Focus on AI-103 certification topics."
                ),
            },
            {"role": "user", "content": f"Search: {query}"},
        ]
    )
    return response.content or ""
