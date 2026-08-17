"""Generator Agent state definition.

The GeneratorState carries all data needed to generate and validate
a new certification question, including domain context, examples,
and optional feedback from prior questions.
"""

from typing import Optional, TypedDict


class GeneratorState(TypedDict):
    """State for the Generator Agent graph.

    Attributes:
        certification: Target certification identifier (e.g. "AI-103").
        target_domain: The domain to generate a question for.
        example_questions: Sample questions for style and difficulty reference.
        feedback_context: Aggregated feedback data (no user IDs) to guide
            generation quality improvements.
        generated_question: The LLM-generated question dict, or None if
            generation has not yet occurred.
        is_valid: Whether the generated question passed format validation.
        validation_errors: List of validation failure reasons (empty if valid).
    """

    certification: str
    target_domain: str
    example_questions: list[dict]
    feedback_context: Optional[list[dict]]
    generated_question: Optional[dict]
    is_valid: bool
    validation_errors: list[str]
