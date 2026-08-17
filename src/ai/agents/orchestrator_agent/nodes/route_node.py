"""Route node for the Orchestrator Agent.

Determines the appropriate action based on session state:
- serve_question: when unanswered questions are available
- generate_new: when all questions are exhausted
- end_session: when the session should terminate
"""

from src.ai.agents.orchestrator_agent.state import OrchestratorState


def route_node(state: OrchestratorState) -> dict:
    """Route to the appropriate action based on current session state.

    Implements the routing logic:
    1. If there are available (unanswered) questions → serve_question
    2. If no questions remain and session is active → generate_new
    3. Otherwise → end_session

    Args:
        state: The current orchestrator state.

    Returns:
        A dict with the "action" key set to the routing decision.
    """
    answered_set = set(state["answered_question_ids"])
    available = state["available_question_ids"]

    # Filter to truly unanswered questions
    unanswered = [qid for qid in available if qid not in answered_set]

    if unanswered:
        return {"action": "serve_question"}

    # No unanswered questions remain
    session_type = state["session_type"]
    if session_type in ("training", "simulation"):
        return {"action": "generate_new"}

    return {"action": "end_session"}


def route_decision(state: OrchestratorState) -> str:
    """Conditional edge function that routes based on the action field.

    Used by the StateGraph to determine the next node after routing.

    Args:
        state: The current orchestrator state with action already set.

    Returns:
        The action string used for conditional edge routing.
    """
    return state["action"]
