"""Progress service for calculating user study progress and weak areas.

Provides progress tracking by aggregating answer records and computing
per-domain performance metrics. Requires both AnswerRepository and
QuestionRepository to resolve question domains from answer records.
"""

from collections import defaultdict

from src.api.domain.repositories.answer_repository import AnswerRepository
from src.api.domain.repositories.question_repository import QuestionRepository

# Minimum number of answers required for detailed analysis
_MINIMUM_ANSWERS_FOR_ANALYSIS = 5

# Number of weakest domains to return
_WEAK_AREAS_COUNT = 3


class ProgressService:
    """Service for computing user progress and identifying weak areas.

    Uses AnswerRepository for fetching user answers and QuestionRepository
    for resolving each question's domain. Caches question lookups within
    a single calculation to avoid redundant queries.
    """

    def __init__(
        self,
        answer_repository: AnswerRepository,
        question_repository: QuestionRepository,
    ) -> None:
        self._answer_repository = answer_repository
        self._question_repository = question_repository

    async def _get_question_domain(
        self, question_id: str, certification: str, cache: dict[str, str]
    ) -> str | None:
        """Look up a question's domain, using an in-memory cache.

        Args:
            question_id: The question document ID.
            certification: The certification partition key.
            cache: A dict mapping question_id to domain string.

        Returns:
            The domain string, or None if the question is not found.
        """
        if question_id in cache:
            return cache[question_id]

        question = await self._question_repository.get_by_id(
            question_id, partition_key=certification
        )
        if question is not None:
            domain = question.get("domain")
            cache[question_id] = domain
            return domain

        return None

    async def calculate_progress(
        self, user_id: str, certification: str = "AI-103"
    ) -> dict:
        """Calculate overall and per-domain progress for a user.

        Returns total answered, overall correct percentage, and correct
        percentage per domain. If the user has fewer than 5 answers,
        returns limited data with an insufficient_data flag.

        Args:
            user_id: The internal user identifier.
            certification: The certification to scope the calculation
                (default: "AI-103").

        Returns:
            A dict with progress data:
            - If >= 5 answers: {"total_answered": int,
              "overall_percentage": float, "per_domain": {domain: float}}
            - If < 5 answers: {"total_answered": int,
              "correct_count": int, "insufficient_data": True}
        """
        answers = await self._answer_repository.get_by_user(user_id)

        total_answered = len(answers)
        correct_count = sum(1 for a in answers if a.get("is_correct"))

        if total_answered < _MINIMUM_ANSWERS_FOR_ANALYSIS:
            return {
                "total_answered": total_answered,
                "correct_count": correct_count,
                "insufficient_data": True,
            }

        # Build domain lookup cache
        question_domain_cache: dict[str, str] = {}

        # Aggregate per-domain stats
        domain_totals: dict[str, int] = defaultdict(int)
        domain_correct: dict[str, int] = defaultdict(int)

        for answer in answers:
            question_id = answer.get("question_id")
            domain = await self._get_question_domain(
                question_id, certification, question_domain_cache
            )
            if domain is None:
                continue

            domain_totals[domain] += 1
            if answer.get("is_correct"):
                domain_correct[domain] += 1

        # Calculate percentages
        overall_percentage = (correct_count / total_answered) * 100

        per_domain: dict[str, float] = {}
        for domain, total in domain_totals.items():
            correct = domain_correct.get(domain, 0)
            per_domain[domain] = (correct / total) * 100

        return {
            "total_answered": total_answered,
            "overall_percentage": overall_percentage,
            "per_domain": per_domain,
        }

    async def get_weak_areas(
        self, user_id: str, certification: str = "AI-103"
    ) -> list[dict[str, str | float]] | dict:
        """Identify the user's top 3 weakest domains.

        Returns the 3 domains with the lowest correct-answer percentage,
        sorted in ascending order of performance. If the user has fewer
        than 5 answers, returns limited data with an insufficient_data flag.

        Args:
            user_id: The internal user identifier.
            certification: The certification to scope the calculation
                (default: "AI-103").

        Returns:
            A list of dicts [{"domain": str, "percentage": float}] for the
            3 weakest domains (ascending by percentage), or a dict with
            insufficient_data flag if fewer than 5 answers.
        """
        progress = await self.calculate_progress(user_id, certification)

        if progress.get("insufficient_data"):
            return progress

        per_domain = progress.get("per_domain", {})

        # Sort domains by percentage ascending (weakest first)
        sorted_domains = sorted(per_domain.items(), key=lambda x: x[1])

        # Return top 3 weakest (or fewer if fewer domains exist)
        weak_areas = [
            {"domain": domain, "percentage": percentage}
            for domain, percentage in sorted_domains[:_WEAK_AREAS_COUNT]
        ]

        return weak_areas
