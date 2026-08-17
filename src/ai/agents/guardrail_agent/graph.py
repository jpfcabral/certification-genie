"""Guardrail Agent graph definition.

Compiles a LangGraph StateGraph that:
1. Classifies user input for safety (classify node)
2. Conditionally responds (safe → pass-through, unsafe → fallback)
"""

from langgraph.graph import END, StateGraph

from src.ai.agents.guardrail_agent.nodes.classify_node import classify_node
from src.ai.agents.guardrail_agent.nodes.respond_node import respond_node
from src.ai.agents.guardrail_agent.state import GuardrailState


def _safety_decision(state: GuardrailState) -> str:
    """Route to respond node regardless of safety — respond_node handles both cases."""
    return "respond"


def build_guardrail_graph():
    """Build and compile the Guardrail Agent graph.

    Flow:
        classify → respond → END

    The classify node uses an LLM to determine input safety.
    The respond node produces the appropriate output:
    - Safe input: output_message=None (pass-through signal)
    - Unsafe input: output_message=FALLBACK_RESPONSE
    """
    graph = StateGraph(GuardrailState)

    # Add nodes
    graph.add_node("classify", classify_node)
    graph.add_node("respond", respond_node)

    # Set entry point
    graph.set_entry_point("classify")

    # classify → respond (always)
    graph.add_edge("classify", "respond")

    # respond → END
    graph.add_edge("respond", END)

    return graph.compile()
