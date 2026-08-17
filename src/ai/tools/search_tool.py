"""Shared Azure documentation search tool for ReAct agents.

Uses a documentation map of learn.microsoft.com to guide the LLM
in producing accurate, grounded documentation excerpts for AI-103
certification topics.
"""

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Maps AI-103 domains to their primary documentation paths on learn.microsoft.com.
# This gives the LLM specific URLs and sections to reference.
DOCS_MAP = {
    "Generative AI and Agents": {
        "urls": [
            "https://learn.microsoft.com/en-us/azure/ai-services/openai/",
            "https://learn.microsoft.com/en-us/azure/ai-services/agents/",
            "https://learn.microsoft.com/en-us/azure/ai-foundry/",
        ],
        "topics": "Azure OpenAI Service, Azure AI Agent Service, Microsoft Foundry, "
                  "RAG patterns, prompt engineering, grounding, model deployment, "
                  "function calling, conversation memory, multi-agent orchestration",
    },
    "Computer Vision": {
        "urls": [
            "https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/",
            "https://learn.microsoft.com/en-us/azure/ai-services/custom-vision/",
        ],
        "topics": "Azure AI Vision, image captioning, OCR, object detection, "
                  "spatial analysis, image generation, video analysis, "
                  "multimodal models, Content Understanding",
    },
    "Text Analysis": {
        "urls": [
            "https://learn.microsoft.com/en-us/azure/ai-services/language/",
            "https://learn.microsoft.com/en-us/azure/ai-services/speech-service/",
            "https://learn.microsoft.com/en-us/azure/ai-services/translator/",
        ],
        "topics": "Azure AI Language, NER, sentiment analysis, key phrase extraction, "
                  "text summarization, Speech-to-Text, Text-to-Speech, translation, "
                  "custom language models",
    },
    "Information Extraction": {
        "urls": [
            "https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/",
            "https://learn.microsoft.com/en-us/azure/search/",
        ],
        "topics": "Azure AI Document Intelligence, form extraction, OCR, "
                  "pre-built vs custom models, Azure AI Search, vector search, "
                  "semantic search, indexers, skillsets, RAG pipelines",
    },
    "Plan and Manage": {
        "urls": [
            "https://learn.microsoft.com/en-us/azure/ai-services/responsible-use-of-ai-overview",
            "https://learn.microsoft.com/en-us/azure/ai-services/content-safety/",
        ],
        "topics": "Responsible AI, content safety, monitoring, security, "
                  "managed identity, RBAC, quotas, scaling, cost management, "
                  "CI/CD pipelines, deployment options",
    },
}


def _build_docs_context(domain: str | None = None) -> str:
    """Build documentation context string for the search prompt."""
    if domain and domain in DOCS_MAP:
        info = DOCS_MAP[domain]
        urls = "\n".join(f"  - {u}" for u in info["urls"])
        return (
            f"Focus area: {domain}\n"
            f"Key topics: {info['topics']}\n"
            f"Primary documentation:\n{urls}"
        )

    # General context for all domains
    all_urls = []
    all_topics = []
    for d, info in DOCS_MAP.items():
        all_urls.extend(info["urls"])
        all_topics.append(f"{d}: {info['topics']}")
    urls_str = "\n".join(f"  - {u}" for u in all_urls[:8])
    topics_str = "\n".join(f"  - {t}" for t in all_topics)
    return (
        f"AI-103 certification domains:\n{topics_str}\n\n"
        f"Key documentation URLs:\n{urls_str}"
    )


@tool
async def search_azure_docs(query: str, domain: str = "") -> str:
    """Search Azure documentation on learn.microsoft.com for AI-103 topics.

    Use this tool when you need factual information about Azure AI services
    to generate questions, explain answers, or respond to user queries.
    Provide a specific query and optionally a domain to focus the search.

    Args:
        query: What to search for (e.g. "Azure AI Document Intelligence pre-built models").
        domain: Optional AI-103 domain to focus on. One of:
                "Generative AI and Agents", "Computer Vision", "Text Analysis",
                "Information Extraction", "Plan and Manage".

    Returns:
        Documentation excerpts with source URLs from learn.microsoft.com.
    """
    from langchain_openai import ChatOpenAI
    from src.api.infrastructure.config import get_settings

    settings = get_settings()
    docs_context = _build_docs_context(domain or None)

    logger.info("[SEARCH] query='%s' domain='%s' model=%s", query[:60], domain, settings.OPENAI_MODEL)

    try:
        llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )

        prompt = (
            "You are a documentation retrieval system for Microsoft Learn (learn.microsoft.com). "
            "Your job is to provide accurate, factual excerpts from official Azure documentation.\n\n"
            f"## Documentation Map\n{docs_context}\n\n"
            f"## Search Query\n{query}\n\n"
            "## Instructions\n"
            "Provide 2-3 relevant documentation excerpts. For each:\n"
            "1. Use ONLY information that exists in official Azure documentation\n"
            "2. Reference real documentation page URLs from the map above\n"
            "3. Be factual and precise — these will be used for certification exam preparation\n\n"
            "Format:\n"
            "---\n"
            "SOURCE: <real learn.microsoft.com URL>\n"
            "CONTENT: <factual excerpt relevant to the query>\n"
            "---"
        )

        response = await llm.ainvoke(prompt)
        logger.info("[SEARCH] Got results for: %s", query[:40])
        return response.content
    except Exception as e:
        logger.error("[SEARCH] Failed: %s", e)
        return f"Search failed: {e}"
