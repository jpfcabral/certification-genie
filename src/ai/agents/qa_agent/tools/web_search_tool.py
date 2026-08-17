"""Web search tool for the QA Agent.

Uses LLM to simulate documentation-aware search, producing factual
excerpts from learn.microsoft.com about Azure AI services and AI-103
certification topics.
"""

import logging

from langchain_openai import ChatOpenAI

from src.api.infrastructure.config import get_settings

logger = logging.getLogger(__name__)


async def web_search(query: str, api_key: str) -> list[dict]:
    """Search for Azure documentation excerpts relevant to the query.

    Uses the LLM to produce documentation-aware search results from
    learn.microsoft.com. In production, this could be replaced with
    Bing Search API or a real web scraper.

    Args:
        query: The search query, typically a user question about Azure AI.
        api_key: OpenAI API key.

    Returns:
        List of search result dicts with keys: 'content', 'source', 'title'.
        Results from learn.microsoft.com are prioritized.
    """
    try:
        settings = get_settings()
        logger.info("[WEB_SEARCH] Searching for: %s (model=%s)", query[:80], settings.OPENAI_MODEL)
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=api_key,
            temperature=0,
        )

        search_prompt = (
            "You are simulating an Azure documentation search engine. "
            "For the query below, provide 3 relevant documentation excerpts "
            "that would appear in Azure's official documentation at "
            "learn.microsoft.com. Each excerpt should be factual and relevant "
            "to the AI-103 certification.\n\n"
            f"Query: {query}\n\n"
            "Respond with 3 documentation excerpts in this exact format:\n"
            "---\n"
            "TITLE: <page title>\n"
            "SOURCE: https://learn.microsoft.com/en-us/azure/ai-services/<path>\n"
            "CONTENT: <relevant excerpt from the documentation>\n"
            "---"
        )

        response = await llm.ainvoke(search_prompt)
        results = _parse_search_results(response.content)
        logger.info("[WEB_SEARCH] Got %d results for: %s", len(results), query[:50])
        return results
    except Exception as e:
        logger.error("[WEB_SEARCH] Failed for query '%s': %s", query[:50], e)
        return []


def _parse_search_results(raw_response: str) -> list[dict]:
    """Parse LLM-generated search results into structured format."""
    results = []
    sections = raw_response.split("---")

    for section in sections:
        section = section.strip()
        if not section:
            continue

        result = {"content": "", "source": "", "title": ""}
        lines = section.split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("TITLE:"):
                result["title"] = line[len("TITLE:"):].strip()
            elif line.startswith("SOURCE:"):
                result["source"] = line[len("SOURCE:"):].strip()
            elif line.startswith("CONTENT:"):
                result["content"] = line[len("CONTENT:"):].strip()
            elif result["content"] and line:
                result["content"] += " " + line

        if result["content"] and result["source"]:
            results.append(result)

    return results


def prioritize_microsoft_sources(results: list[dict]) -> list[dict]:
    """Sort search results to prioritize learn.microsoft.com sources."""
    microsoft_results = []
    other_results = []

    for result in results:
        source = result.get("source", "")
        if "learn.microsoft.com" in source:
            microsoft_results.append(result)
        else:
            other_results.append(result)

    return microsoft_results + other_results
