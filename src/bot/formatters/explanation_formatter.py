TELEGRAM_MESSAGE_LIMIT = 4096

TRUNCATION_SUFFIX = "\n\n… (truncated)"


def format_explanation(
    explanation: str,
    question_text: str | None = None,
    correct_option: str | None = None,
) -> str:
    """Format an explanation for Telegram, respecting the 4096 character limit.

    Args:
        explanation: The explanation text (short or detailed).
        question_text: Optional question text to include as header context.
        correct_option: Optional correct answer text to highlight.

    Returns:
        Formatted explanation string within 4096 chars.
    """
    parts: list[str] = []

    if question_text:
        parts.append(f"❓ *{question_text}*")
        parts.append("")

    if correct_option:
        parts.append(f"✅ Correct answer: {correct_option}")
        parts.append("")

    parts.append(explanation)

    result = "\n".join(parts)
    return _truncate(result)


def _truncate(text: str) -> str:
    """Truncate text to fit within the Telegram message limit while preserving readability."""
    if len(text) <= TELEGRAM_MESSAGE_LIMIT:
        return text

    max_len = TELEGRAM_MESSAGE_LIMIT - len(TRUNCATION_SUFFIX)
    # Cut at the last newline before the limit to avoid mid-sentence truncation
    truncated = text[:max_len]
    last_newline = truncated.rfind("\n")
    if last_newline > max_len * 0.8:
        truncated = truncated[:last_newline]

    return truncated + TRUNCATION_SUFFIX
