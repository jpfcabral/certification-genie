"""QA Agent graph definition.

Compiles the LangGraph StateGraph for the QA Agent:
search → answer

The QA Agent answers free-form questions about Azure AI Services using RAG.
It searches Azure documentation (via vector store and web search), then
synthesizes an answer with proper citations.
"""

from langgraph.graph import END, StateGraph

from src.ai.agents.qa_agent.nodes.answer_node import answer_node
from src.ai.agents.qa_agent.nodes.search_node import search_node
from src.ai.agents.qa_agent.state import QAState


def build_qa_graph() -> StateGraph:
    """Build and compile the QA Agent graph.

    The graph follows a simple two-step pipeline:
    1. search — Searches Azure documentation via RAG (vector store + web search)
    2. answer — Synthesizes a response with citations from search results

    The agent handles:
    - Scope checking (only Azure AI / AI-103 topics)
    - Graceful degradation when search fails
    - Source citation in responses
    - Prioritization of learn.microsoft.com sources

    Returns:
        Compiled StateGraph ready for invocation.
    """
    graph = StateGraph(QAState)

    # Add nodes
    graph.add_node("search", search_node)
    graph.add_node("answer", answer_node)

    # Define edges: search → answer → END
    graph.set_entry_point("search")
    graph.add_edge("search", "answer")
    graph.add_edge("answer", END)

    return graph.compile()
