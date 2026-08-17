"""Explainer Agent — ReAct pattern with web search.

Provides detailed explanations for incorrect answers, searching
Azure documentation for authoritative context and references.
"""

import logging

from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

from src.ai.tools.search_tool import search_azure_docs
from src.api.infrastructure.config import get_settings

logger = logging.getLogger(__name__)

EXPLAINER_SYSTEM_PROMPT = """You are a certification exam tutor for the Azure AI-103 exam.

## Your Role
Explain why a specific answer is correct and why the other options are wrong.
Provide authoritative explanations grounded in Azure documentation.

## Instructions
1. Use the search_azure_docs tool to find documentation about the correct answer's concept
2. Explain clearly:
   - Why the correct answer is right (with documentation evidence)
   - Why each wrong option is incorrect
   - A key takeaway for exam preparation
3. Keep the total response under 4000 characters (Telegram limit)
4. Cite documentation sources

## Response Format
**Correct Answer:** [letter and text]

**Why it's correct:**
[Explanation grounded in docs]

**Why others are wrong:**
- [Option]: [Why wrong]

**Key Concept:**
[One-sentence takeaway]

**Sources:**
- [URL from search]
"""


def build_explainer_graph():
    """Build the Explainer Agent using ReAct pattern with web search.

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
        prompt=EXPLAINER_SYSTEM_PROMPT,
    )

    return agent
