"""Question service for managing question lifecycle.

Handles retrieving unanswered questions, validating and persisting new
questions (with duplicate detection), and deactivating low-quality questions.
"""

import logging

from src.api.domain.models.question import Question
from src.api.domain.repositories.answer_repository import AnswerRepository
from src.api.domain.repositories.question_repository import QuestionRepository

logger = logging.getLogger(__name__)


class DuplicateQuestionError(Exception):
    """Raised when a question is detected as a duplicate of an existing one."""

    pass


class QuestionValidationError(Exception):
    """Raised when a question fails format validation."""

    pass


def _normalize_text(text: str) -> str:
    """Normalize question text for duplicate comparison.

    Strips whitespace and converts to lowercase for case-insensitive
    comparison.

    Args:
        text: The raw question text.

    Returns:
        Normalized text string.
    """
    return " ".join(text.strip().lower().split())


class QuestionService:
    """Service for question management operations.

    Provides methods for retrieving unanswered questions filtered by
    certification, validating and persisting new questions with duplicate
    detection, and deactivating low-quality questions.
    """

    def __init__(
        self,
        question_repository: QuestionRepository,
        answer_repository: AnswerRepository,
    ) -> None:
        self._question_repository = question_repository
        self._answer_repository = answer_repository

    async def get_unanswered_questions(
        self, user_id: str, certification: str
    ) -> list[dict]:
        """Return active questions not yet answered by the user.

        Fetches all active questions for the given certification, then
        excludes any that the user has already answered.

        Args:
            user_id: The internal user identifier.
            certification: The certification filter (e.g., "AI-103").

        Returns:
            A list of question documents the user has not yet answered,
            filtered by certification.
        """
        active_questions = (
            await self._question_repository.get_active_by_certification(certification)
        )

        answered_ids = await self._answer_repository.get_answered_question_ids(user_id)
        answered_set = set(answered_ids)

        unanswered = [
            q for q in active_questions if q["id"] not in answered_set
        ]

        return unanswered

    async def validate_and_persist_question(self, question: Question) -> dict:
        """Validate a question's format and persist it if not a duplicate.

        Validates that the question has exactly 4 options, a correct_answer_index
        between 0-3, and a short_explanation of at most 200 characters. Then
        checks for duplicates by comparing normalized question text against
        existing questions in the same certification.

        Args:
            question: A Question model instance to validate and persist.

        Returns:
            The persisted question document.

        Raises:
            QuestionValidationError: If the question fails format validation.
            DuplicateQuestionError: If a duplicate question is detected.
        """
        # Validate format (Pydantic validators handle most of this,
        # but we add explicit checks for clarity and custom error messages)
        if len(question.options) != 4:
            raise QuestionValidationError(
                "Question must have exactly 4 options"
            )

        if question.correct_answer_index < 0 or question.correct_answer_index > 3:
            raise QuestionValidationError(
                "Correct answer index must be between 0 and 3"
            )

        if len(question.short_explanation) > 200:
            raise QuestionValidationError(
                "Short explanation must be at most 200 characters"
            )

        # Check for duplicates within the same certification
        existing_questions = (
            await self._question_repository.get_active_by_certification(
                question.certification
            )
        )

        normalized_new = _normalize_text(question.text)
        for existing in existing_questions:
            normalized_existing = _normalize_text(existing["text"])
            if normalized_new == normalized_existing:
                raise DuplicateQuestionError(
                    f"Duplicate question detected: text matches existing "
                    f"question '{existing['id']}'"
                )

        # Persist the question
        question_doc = question.model_dump(mode="json")
        result = await self._question_repository.create(question_doc)

        logger.info(
            "Persisted new question '%s' for certification '%s'",
            question.id,
            question.certification,
        )

        return result

    async def deactivate_low_quality_questions(
        self, threshold: float, certification: str
    ) -> list[dict]:
        """Deactivate questions with quality_score below the threshold.

        Fetches all active questions for the given certification and
        marks any with a quality_score below the threshold as inactive.

        Args:
            threshold: The minimum quality score. Questions scoring below
                this value will be deactivated.
            certification: The certification to scope the deactivation.

        Returns:
            A list of deactivated question documents.
        """
        active_questions = (
            await self._question_repository.get_active_by_certification(certification)
        )

        deactivated = []
        for question in active_questions:
            if question.get("quality_score", 1.0) < threshold:
                result = await self._question_repository.deactivate(
                    question["id"], certification
                )
                if result is not None:
                    deactivated.append(result)
                    logger.info(
                        "Deactivated question '%s' (score: %.2f, threshold: %.2f)",
                        question["id"],
                        question.get("quality_score", 1.0),
                        threshold,
                    )

        return deactivated
