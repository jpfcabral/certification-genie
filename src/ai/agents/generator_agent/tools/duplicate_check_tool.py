"""Duplicate check tool — compares a new question against the existing bank.

Uses text similarity (normalized comparison) to detect if a generated question
is too similar to existing questions. This prevents adding near-duplicate
questions to the question bank.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Similarity threshold: questions with normalized similarity above this
# are considered duplicates.
DUPLICATE_THRESHOLD = 0.85


def _normalize_text(text: str) -> str:
    """Normalize text for comparison by lowering case and stripping punctuation."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _compute_similarity(text_a: str, text_b: str) -> float:
    """Compute word-overlap (Jaccard) similarity between two texts.

    Returns a float between 0.0 (no overlap) and 1.0 (identical).
    """
    words_a = set(_normalize_text(text_a).split())
    words_b = set(_normalize_text(text_b).split())

    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def check_duplicate(
    new_question_text: str,
    existing_questions: list[dict],
    threshold: float = DUPLICATE_THRESHOLD,
) -> dict:
    """Check if a new question is a duplicate of any existing question.

    Compares the new question text against all existing questions using
    word-overlap (Jaccard) similarity. Returns whether a duplicate was
    found and the most similar existing question if above the threshold.

    Args:
        new_question_text: The text of the newly generated question.
        existing_questions: List of existing question dicts with at least
            a "text" key.
        threshold: Similarity threshold above which questions are considered
            duplicates (default: 0.85).

    Returns:
        Dict with:
            - is_duplicate (bool): True if a duplicate was found.
            - most_similar_text (str | None): Text of the most similar
                existing question, or None if no close match.
            - similarity_score (float): Highest similarity score found.
    """
    if not new_question_text or not existing_questions:
        return {
            "is_duplicate": False,
            "most_similar_text": None,
            "similarity_score": 0.0,
        }

    max_similarity = 0.0
    most_similar_text = None

    for existing in existing_questions:
        existing_text = existing.get("text", "")
        if not existing_text:
            continue

        similarity = _compute_similarity(new_question_text, existing_text)
        if similarity > max_similarity:
            max_similarity = similarity
            most_similar_text = existing_text

    is_duplicate = max_similarity >= threshold

    if is_duplicate:
        logger.info(
            "Duplicate detected (score=%.2f): %s",
            max_similarity,
            most_similar_text[:80] if most_similar_text else "",
        )

    return {
        "is_duplicate": is_duplicate,
        "most_similar_text": most_similar_text if is_duplicate else None,
        "similarity_score": max_similarity,
    }
