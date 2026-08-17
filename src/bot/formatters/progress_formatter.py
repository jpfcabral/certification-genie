def format_progress_summary(
    total_answered: int,
    overall_percentage: float,
    domain_breakdown: dict[str, float],
) -> str:
    """Format progress summary with per-domain breakdown.

    Args:
        total_answered: Total number of questions answered.
        overall_percentage: Overall correct-answer percentage (0-100).
        domain_breakdown: Mapping of domain name to correct percentage (0-100).

    Returns:
        Formatted string for Telegram message.
    """
    lines: list[str] = [
        "📊 *Your Progress*",
        "",
        f"Total questions answered: {total_answered}",
        f"Overall score: {overall_percentage:.1f}%",
        "",
        "*Per-domain breakdown:*",
    ]

    for domain, percentage in domain_breakdown.items():
        bar = _progress_bar(percentage)
        lines.append(f"  • {domain}: {percentage:.1f}% {bar}")

    return "\n".join(lines)


def _progress_bar(percentage: float, length: int = 10) -> str:
    """Generate a text-based progress bar."""
    filled = round(percentage / 100 * length)
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"
