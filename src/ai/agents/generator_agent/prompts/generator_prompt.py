"""Prompt builder for the Generator Agent.

Constructs a system prompt that instructs the LLM to generate a certification
question with domain description, example questions for style/difficulty
reference, and optional feedback context for quality improvement.
"""

from typing import Optional

SYSTEM_PROMPT_TEMPLATE = """You are an expert certification question writer for the {certification} exam.

## Your Task
Generate a new multiple-choice question for the domain: "{target_domain}".

## STRICT Requirements
- The question text MUST be at most 255 characters.
- The question MUST have exactly 4 answer options (labeled A, B, C, D).
- Each answer option MUST be at most 90 characters. Keep options concise and clear.
- Exactly ONE option must be correct.
- Provide a short_explanation (max 200 characters) summarizing why the correct answer is right.
- Provide a detailed_explanation with a thorough breakdown of the correct answer and why alternatives are incorrect.
- The question must be at certification exam difficulty level.
- The question must be unique and not a rephrasing of the provided examples.

## Domain Description
Domain: {target_domain}
Certification: {certification}

## Example Questions (for style and difficulty reference)
{examples_section}

{feedback_section}

## Output Format
Respond ONLY with a valid JSON object in the following format (no markdown fences):
{{
    "text": "The question text here? (max 255 chars)",
    "options": ["Short option A (max 90 chars)", "Option B", "Option C", "Option D"],
    "correct_answer_index": 0,
    "short_explanation": "Brief explanation (max 200 chars)",
    "detailed_explanation": "Full detailed explanation of the correct answer and why others are wrong."
}}
"""


def _format_examples(example_questions: list[dict]) -> str:
    """Format example questions for inclusion in the prompt."""
    if not example_questions:
        return "No examples available. Generate a question appropriate for the domain and certification level."

    lines: list[str] = []
    for i, q in enumerate(example_questions, start=1):
        text = q.get("text", "")
        options = q.get("options", [])
        correct_idx = q.get("correct_answer_index", 0)
        options_str = "\n".join(
            f"  {'*' if j == correct_idx else ' '} {chr(65 + j)}. {opt}"
            for j, opt in enumerate(options)
        )
        lines.append(f"Example {i}:\n  Q: {text}\n{options_str}")

    return "\n\n".join(lines)


def _format_feedback(feedback_context: Optional[list[dict]]) -> str:
    """Format aggregated feedback context for the prompt."""
    if not feedback_context:
        return ""

    lines = ["## Feedback from Previous Questions (use to improve quality)"]
    for fb in feedback_context:
        flag_type = fb.get("flag_type", "general")
        count = fb.get("count", 1)
        comment = fb.get("comment", "")
        detail = f" — \"{comment}\"" if comment else ""
        lines.append(f"- Issue: {flag_type} (reported {count} time(s)){detail}")

    lines.append(
        "\nAvoid the issues described above in the question you generate."
    )
    return "\n".join(lines)


def build_generator_prompt(
    certification: str,
    target_domain: str,
    example_questions: list[dict],
    feedback_context: Optional[list[dict]] = None,
) -> str:
    """Build the full system prompt for question generation.

    Args:
        certification: Target certification (e.g. "AI-103").
        target_domain: The specific domain area.
        example_questions: Sample questions for style reference.
        feedback_context: Optional aggregated feedback data (no user IDs).

    Returns:
        Formatted system prompt string.
    """
    examples_section = _format_examples(example_questions)
    feedback_section = _format_feedback(feedback_context)

    return SYSTEM_PROMPT_TEMPLATE.format(
        certification=certification,
        target_domain=target_domain,
        examples_section=examples_section,
        feedback_section=feedback_section,
    )
