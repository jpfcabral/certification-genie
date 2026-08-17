"""Generator Agent — ReAct pattern with web search.

Uses a reasoning-action loop to:
1. Search Azure documentation for the target domain
2. Generate a certification question grounded in real docs
3. Validate format constraints (options ≤100 chars, text ≤300, etc.)
"""

import json
import logging

from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

from src.ai.tools.search_tool import search_azure_docs
from src.api.infrastructure.config import get_settings

logger = logging.getLogger(__name__)

GENERATOR_SYSTEM_PROMPT = """You are an expert certification question writer for the AI-103 (Developing AI Apps and Agents on Azure) exam.

## Your Task
1. FIRST, use the search_azure_docs tool to find current, factual information about the target domain
2. THEN generate a high-quality multiple-choice question based on the search results

## STRICT Format Rules
- Question text: max 255 characters
- Exactly 4 answer options, each max 90 characters
- Exactly 1 correct answer (correct_answer_index: 0-3)
- short_explanation: max 200 characters
- detailed_explanation: thorough breakdown

## Output
After searching, respond with ONLY a JSON object (no markdown fences):
{{
    "text": "Question text (max 255 chars)",
    "options": ["A (max 90)", "B (max 90)", "C (max 90)", "D (max 90)"],
    "correct_answer_index": 0,
    "short_explanation": "Why correct (max 200 chars)",
    "detailed_explanation": "Full explanation with references to documentation found."
}}

## Important
- Use CURRENT Azure service names (Foundry Tools, Azure Vision, etc.)
- Questions should be scenario-based when possible
- Ground your question in the documentation you found via search
"""


def build_generator_graph():
    """Build the Generator Agent using ReAct pattern with web search.

    The agent will:
    1. Search Azure docs for the target domain
    2. Generate a question grounded in the search results
    3. Return structured JSON

    Returns:
        A compiled ReAct agent graph.
    """
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.7,
    )

    agent = create_react_agent(
        model=llm,
        tools=[search_azure_docs],
        prompt=GENERATOR_SYSTEM_PROMPT,
    )

    return agent
