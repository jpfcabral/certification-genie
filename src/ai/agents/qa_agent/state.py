"""QA Agent state definition.

Defines the typed state that flows through the QA Agent's LangGraph nodes.
"""

from typing import TypedDict


class QAState(TypedDict):
    """State for the QA Agent graph.

    Attributes:
        user_query: The free-form question asked by the user.
        search_results: List of documents retrieved from RAG search,
            each containing 'content', 'source', and 'title' keys.
        answer: The synthesized answer with citations.
        sources: List of documentation URLs/references used in the answer.
        is_in_scope: Whether the query is within Azure AI Services / AI-103 scope.
    """

    user_query: str
    search_results: list[dict]
    answer: str
    sources: list[str]
    is_in_scope: bool
