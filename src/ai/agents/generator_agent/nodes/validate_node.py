"""Validate node — checks that a generated question meets format requirements.

Validation rules:
- Must have exactly 4 options
- correct_answer_index must be between 0 and 3
- short_explanation must be at most 200 characters
- detailed_explanation must be non-empty
- text (question body) must be non-empty
"""

import logging

from src.ai.agents.generator_agent.state import GeneratorState

logger = logging.getLogger(__name__)


def validate_node(state: GeneratorState) -> dict:
    """Validate the generated question format.

    Checks that the generated question conforms to all required constraints:
    exactly 4 options, valid correct_answer_index, explanation length limits.

    Args:
        state: Current generator state with generated_question.

    Returns:
        Partial state update with is_valid and validation_errors.
    """
    question = state.get("generated_question")
    errors: list[str] = []

    if question is None:
        return {
            "is_valid": False,
            "validation_errors": ["No question was generated"],
        }

    # Validate question text
    text = question.get("text")
    if not text or not isinstance(text, str) or not text.strip():
        errors.append("Question text is missing or empty")

    # Validate options
    options = question.get("options")
    if not isinstance(options, list):
        errors.append("Options must be a list")
    elif len(options) != 4:
        errors.append(f"Question must have exactly 4 options, got {len(options)}")
    else:
        for i, opt in enumerate(options):
            if not isinstance(opt, str) or not opt.strip():
                errors.append(f"Option {i} is missing or empty")
            elif len(opt) > 100:
                errors.append(
                    f"Option {i} exceeds 100 characters ({len(opt)} chars). "
                    f"Telegram poll options must be ≤100 chars."
                )

    # Validate question text length (Telegram limit: 300 chars)
    if text and isinstance(text, str) and len(text) > 300:
        errors.append(
            f"Question text exceeds 300 characters ({len(text)} chars). "
            f"Telegram poll questions must be ≤300 chars."
        )

    # Validate correct_answer_index
    correct_idx = question.get("correct_answer_index")
    if correct_idx is None:
        errors.append("correct_answer_index is missing")
    elif not isinstance(correct_idx, int):
        errors.append("correct_answer_index must be an integer")
    elif correct_idx < 0 or correct_idx > 3:
        errors.append(
            f"correct_answer_index must be between 0 and 3, got {correct_idx}"
        )

    # Validate short_explanation
    short_exp = question.get("short_explanation")
    if not short_exp or not isinstance(short_exp, str) or not short_exp.strip():
        errors.append("short_explanation is missing or empty")
    elif len(short_exp) > 200:
        errors.append(
            f"short_explanation must be at most 200 characters, got {len(short_exp)}"
        )

    # Validate detailed_explanation
    detailed_exp = question.get("detailed_explanation")
    if (
        not detailed_exp
        or not isinstance(detailed_exp, str)
        or not detailed_exp.strip()
    ):
        errors.append("detailed_explanation is missing or empty")

    is_valid = len(errors) == 0

    if is_valid:
        logger.info("Generated question passed validation")
    else:
        logger.warning("Generated question failed validation: %s", errors)

    return {
        "is_valid": is_valid,
        "validation_errors": errors,
    }
