"""Explainer Agent graph definition.

Compiles a LangGraph StateGraph that:
1. Explains the correct answer and why alternatives are wrong
2. Conditionally enriches with documentation when the user asks "why"/"explain"

The graph flow is: explain → (conditional) enrich → END
"""

from langgraph.graph import END, StateGraph

from src.ai.agents.explainer_agent.nodes.enrich_node import enrich_node
from src.ai.agents.explainer_agent.nodes.explain_node import explain_node
from src.ai.agents.explainer_agent.state import ExplainerState


def _needs_enrichment(state: ExplainerState) -> str:
    """Determine whether to enrich the explanation with documentation.

    Routes to the enrich node when the user has explicitly asked for
    more detail (e.g., "why" or "explain").

    Args:
        state: Current explainer state.

    Returns:
        "enrich" if enrichment is needed, "end" otherwise.
    """
    if state.get("needs_enrichment", False):
        return "enrich"
    return "end"


def build_explainer_graph() -> StateGraph:
    """Build and compile the Explainer Agent graph.

    Graph flow:
        explain → conditional edge:
            - if needs_enrichment: enrich → END
            - otherwise: END

    The agent receives only question content (no user identifiers)
    and produces explanations within the 4096 character Telegram limit.

    Returns:
        Compiled StateGraph for the Explainer Agent.
    """
    graph = StateGraph(ExplainerState)

    # Add nodes
    graph.add_node("explain", explain_node)
    graph.add_node("enrich", enrich_node)

    # Set entry point
    graph.set_entry_point("explain")

    # Add conditional edge from explain
    graph.add_conditional_edges(
        "explain",
        _needs_enrichment,
        {
            "enrich": "enrich",
            "end": END,
        },
    )

    # Enrich always goes to END
    graph.add_edge("enrich", END)

    return graph.compile()
