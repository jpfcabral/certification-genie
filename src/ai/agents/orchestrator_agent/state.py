"""State definition for the Orchestrator Agent.

The Orchestrator Agent manages session flow and decides which question
to serve next. It routes requests to appropriate actions based on
session type, available questions, and domain weights.
"""

from typing import Optional, TypedDict


class OrchestratorState(TypedDict):
    """Typed state for the Orchestrator Agent graph.

    Attributes:
        session_type: The current session type ("training", "simulation", "free_qa").
        certification: The target certification (e.g., "AI-103").
        domain_weights: Mapping of domain name to weight fraction for
            question distribution.
        answered_question_ids: List of question IDs already answered by the user.
        available_question_ids: List of question IDs available to serve.
        selected_question_id: The next question to serve, or None.
        action: The routing decision — one of "serve_question",
            "generate_new", or "end_session".
    """

    session_type: str
    certification: str
    domain_weights: dict[str, float]
    answered_question_ids: list[str]
    available_question_ids: list[str]
    selected_question_id: Optional[str]
    action: str
