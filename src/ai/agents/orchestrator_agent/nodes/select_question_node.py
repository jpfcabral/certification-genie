"""Select question node for the Orchestrator Agent.

Selects the next question to serve, prioritizing unanswered questions
and using random order within the available pool. Ensures that
already-answered questions are never served while unanswered ones
remain available.
"""

import random

from src.ai.agents.orchestrator_agent.state import OrchestratorState


def select_question_node(state: OrchestratorState) -> dict:
    """Select the next question to serve from the available pool.

    Prioritizes unanswered questions — filters out any already-answered
    IDs and randomly selects from the remaining set. This ensures
    Property 6 (question selection prioritizes unanswered) is satisfied.

    If no unanswered questions remain, sets selected_question_id to None.

    Args:
        state: The current orchestrator state containing available and
            answered question ID lists.

    Returns:
        A dict with "selected_question_id" set to the chosen question
        or None, and "available_question_ids" updated to reflect only
        unanswered questions.
    """
    answered_set = set(state["answered_question_ids"])
    available = state["available_question_ids"]

    # Filter to only unanswered questions
    unanswered = [qid for qid in available if qid not in answered_set]

    if not unanswered:
        return {
            "selected_question_id": None,
            "available_question_ids": [],
        }

    # Random selection from unanswered pool
    selected = random.choice(unanswered)

    return {
        "selected_question_id": selected,
        "available_question_ids": unanswered,
    }
