from typing import Optional, TypedDict


class ExplainerState(TypedDict):
    """State for the Explainer Agent graph.

    Contains the question context, user's answer, and explanation outputs.
    The agent never receives user identifiers — only question content.
    """

    question_text: str
    options: list[str]
    correct_answer_index: int
    user_selected_index: int
    short_explanation: str
    detailed_explanation: str
    enriched_explanation: Optional[str]
    documentation_sources: list[str]
    needs_enrichment: bool  # True when user asks "why"/"explain"
