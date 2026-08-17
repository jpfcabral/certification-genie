"""QA Agent — ReAct pattern with web search.

Answers free-form questions about Azure AI services using a
reasoning-action loop that searches documentation before answering.
"""

import logging

from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

from src.ai.tools.search_tool import search_azure_docs
from src.api.infrastructure.config import get_settings

logger = logging.getLogger(__name__)

QA_SYSTEM_PROMPT = """You are an Azure AI-103 certification study assistant.

## Your Role
Answer questions about Azure AI Services, Microsoft Foundry, and topics covered by the AI-103 exam.

## Instructions
1. ALWAYS use the search_azure_docs tool FIRST to find relevant documentation
2. Base your answer on the search results — cite sources with URLs
3. If the search doesn't return useful results, say so and suggest checking learn.microsoft.com
4. Keep answers concise but thorough (under 4000 characters for Telegram)
5. Use current Azure service names (Foundry Tools, Azure Vision, etc.)

## Scope
Only answer questions about:
- Azure AI Services / Foundry Tools
- Microsoft Foundry platform
- Azure OpenAI Service
- Computer Vision, Speech, Language, Document Intelligence
- Azure AI Search, Content Understanding
- RAG patterns, Agent architectures
- Responsible AI principles

If the question is out of scope, politely decline.

## Response Format
After searching, provide a clear answer with:
- Direct answer to the question
- Key details from documentation
- Source citations [Source: URL]
"""


def build_qa_graph():
    """Build the QA Agent using ReAct pattern with web search.

    Returns:
        A compiled ReAct agent graph.
    """
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.3,
    )

    agent = create_react_agent(
        model=llm,
        tools=[search_azure_docs],
        prompt=QA_SYSTEM_PROMPT,
    )

    return agent
