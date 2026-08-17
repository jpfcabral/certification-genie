"""Tool for fetching available questions for the Orchestrator Agent.

Provides a LangChain-compatible tool that queries the question repository
to retrieve available (unanswered) question IDs for a given certification,
filtered by domain weights.
"""

from typing import Optional

from langchain_core.tools import tool


@tool
def fetch_available_questions(
    certification: str,
    answered_question_ids: list[str],
    available_question_ids: list[str],
    domain_weights: Optional[dict[str, float]] = None,
) -> dict[str, list[str]]:
    """Fetch available questions excluding already answered ones.

    Filters the available_question_ids by removing any that appear in
    answered_question_ids. This is a pure filtering tool that operates
    on pre-loaded data rather than making database calls directly.

    Args:
        certification: The certification filter (e.g., "AI-103").
        answered_question_ids: Question IDs already answered by the user.
        available_question_ids: All question IDs available in the bank.
        domain_weights: Optional domain weight mapping for prioritization.

    Returns:
        A dict with key "unanswered_ids" containing the filtered list.
    """
    answered_set = set(answered_question_ids)
    unanswered = [
        qid for qid in available_question_ids if qid not in answered_set
    ]

    return {"unanswered_ids": unanswered}
