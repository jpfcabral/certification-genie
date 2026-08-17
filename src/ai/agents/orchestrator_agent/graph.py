"""Orchestrator Agent graph definition.

Compiles a LangGraph StateGraph that routes session requests to the
appropriate action and selects questions for study sessions.

Graph flow:
    route → (conditional)
        ├── serve_question → select_question → END
        ├── generate_new → END
        └── end_session → END
"""

from langgraph.graph import END, StateGraph

from src.ai.agents.orchestrator_agent.nodes.route_node import (
    route_decision,
    route_node,
)
from src.ai.agents.orchestrator_agent.nodes.select_question_node import (
    select_question_node,
)
from src.ai.agents.orchestrator_agent.state import OrchestratorState


def build_orchestrator_graph() -> StateGraph:
    """Build and compile the Orchestrator Agent graph.

    The graph routes incoming session state to the appropriate action:
    - serve_question: selects the next unanswered question
    - generate_new: signals that question generation is needed
    - end_session: signals session termination

    Returns:
        A compiled LangGraph StateGraph ready for invocation.
    """
    graph = StateGraph(OrchestratorState)

    # Add nodes
    graph.add_node("route", route_node)
    graph.add_node("select_question", select_question_node)

    # Set entry point
    graph.set_entry_point("route")

    # Add conditional edges from route node
    graph.add_conditional_edges(
        "route",
        route_decision,
        {
            "serve_question": "select_question",
            "generate_new": END,
            "end_session": END,
        },
    )

    # select_question always leads to END
    graph.add_edge("select_question", END)

    return graph.compile()
