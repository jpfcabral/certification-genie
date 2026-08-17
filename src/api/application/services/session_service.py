"""Session service for managing user study sessions.

Handles lifecycle management for training, simulation, and free Q&A
sessions. Enforces the constraint that only one active session per user
may exist at a time.
"""

import logging
import math
import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.api.domain.enums.domain_type import DomainType, get_domain_weights
from src.api.domain.models.answer_record import AnswerRecord
from src.api.domain.models.session import Session
from src.api.domain.repositories.answer_repository import AnswerRepository
from src.api.domain.repositories.question_repository import QuestionRepository
from src.api.domain.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)

DEFAULT_CERTIFICATION = "AI-103"


class ActiveSessionExistsError(Exception):
    """Raised when attempting to start a session while one is already active."""

    pass


class NoActiveSessionError(Exception):
    """Raised when an operation requires an active session but none exists."""

    pass


class SessionService:
    """Service for user session lifecycle management.

    Manages training, simulation, and free Q&A sessions. Ensures only
    one active session per user at a time. Handles answer recording,
    correctness determination, and session advancement.
    """

    def __init__(
        self,
        session_repository: SessionRepository,
        question_repository: QuestionRepository,
        answer_repository: AnswerRepository,
    ) -> None:
        self._session_repository = session_repository
        self._question_repository = question_repository
        self._answer_repository = answer_repository

    async def start_training(
        self, user_id: str, certification: str = DEFAULT_CERTIFICATION
    ) -> Session:
        """Start a training session for the user.

        Creates a new training session and selects the first unanswered
        question. Ends any existing active session before starting.

        Args:
            user_id: The internal user identifier.
            certification: The certification to train for.

        Returns:
            The created training Session with the first question queued.

        Raises:
            ActiveSessionExistsError: If the user already has an active session.
        """
        existing = await self._session_repository.get_active_session(user_id)
        if existing is not None:
            raise ActiveSessionExistsError(
                f"User '{user_id}' already has an active session: "
                f"'{existing['id']}'"
            )

        # Get unanswered questions for this user
        unanswered = await self._get_unanswered_questions(user_id, certification)

        # Select first question (random from unanswered pool)
        questions_served = []
        if unanswered:
            first_question = random.choice(unanswered)
            questions_served = [first_question["id"]]

        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_type="training",
            started_at=datetime.now(timezone.utc),
            questions_served=questions_served,
            current_question_index=0,
            is_active=True,
        )

        session_doc = session.model_dump(mode="json")
        await self._session_repository.create_session(session_doc)

        logger.info(
            "Started training session '%s' for user '%s'",
            session.id,
            user_id,
        )

        return session

    async def start_simulation(
        self,
        user_id: str,
        num_questions: int = 20,
        certification: str = DEFAULT_CERTIFICATION,
    ) -> Session:
        """Start a simulation session with domain-proportional distribution.

        Creates a simulation session with questions distributed across
        domains according to the AI-103 exam weights.

        Args:
            user_id: The internal user identifier.
            num_questions: Number of questions in the simulation (default 20).
            certification: The certification to simulate.

        Returns:
            The created simulation Session with questions selected.

        Raises:
            ActiveSessionExistsError: If the user already has an active session.
        """
        existing = await self._session_repository.get_active_session(user_id)
        if existing is not None:
            raise ActiveSessionExistsError(
                f"User '{user_id}' already has an active session: "
                f"'{existing['id']}'"
            )

        # Select questions proportional to domain weights
        selected_question_ids = await self._select_simulation_questions(
            user_id, num_questions, certification
        )

        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_type="simulation",
            started_at=datetime.now(timezone.utc),
            questions_served=selected_question_ids,
            current_question_index=0,
            total_questions=num_questions,
            is_active=True,
        )

        session_doc = session.model_dump(mode="json")
        await self._session_repository.create_session(session_doc)

        logger.info(
            "Started simulation session '%s' for user '%s' with %d questions",
            session.id,
            user_id,
            num_questions,
        )

        return session

    async def start_free_qa(self, user_id: str) -> Session:
        """Start a free Q&A session for the user.

        Creates a conversational session where the user can ask free-form
        questions about Azure AI topics.

        Args:
            user_id: The internal user identifier.

        Returns:
            The created free Q&A Session.

        Raises:
            ActiveSessionExistsError: If the user already has an active session.
        """
        existing = await self._session_repository.get_active_session(user_id)
        if existing is not None:
            raise ActiveSessionExistsError(
                f"User '{user_id}' already has an active session: "
                f"'{existing['id']}'"
            )

        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_type="free_qa",
            started_at=datetime.now(timezone.utc),
            is_active=True,
        )

        session_doc = session.model_dump(mode="json")
        await self._session_repository.create_session(session_doc)

        logger.info(
            "Started free Q&A session '%s' for user '%s'",
            session.id,
            user_id,
        )

        return session

    async def end_session(self, user_id: str) -> Optional[dict]:
        """End the user's active session.

        Marks the session as ended. For simulation sessions, returns a
        summary dict with score and per-domain performance.

        Args:
            user_id: The internal user identifier.

        Returns:
            A summary dict for simulation sessions (with score, total,
            per_domain breakdown), or None for other session types.

        Raises:
            NoActiveSessionError: If no active session exists.
        """
        session_doc = await self._session_repository.get_active_session(user_id)
        if session_doc is None:
            raise NoActiveSessionError(
                f"User '{user_id}' has no active session to end"
            )

        session_doc["is_active"] = False
        session_doc["ended_at"] = datetime.now(timezone.utc).isoformat()
        await self._session_repository.update_session(session_doc)

        logger.info(
            "Ended session '%s' (type: %s) for user '%s'",
            session_doc["id"],
            session_doc["session_type"],
            user_id,
        )

        # Return summary for simulation sessions
        if session_doc["session_type"] == "simulation":
            return await self._build_simulation_summary(
                user_id, session_doc["id"]
            )

        return None

    async def get_current_session(self, user_id: str) -> Optional[Session]:
        """Get the user's current active session.

        Args:
            user_id: The internal user identifier.

        Returns:
            The active Session model, or None if no active session.
        """
        session_doc = await self._session_repository.get_active_session(user_id)
        if session_doc is None:
            return None

        return Session(**{
            "id": session_doc["id"],
            "user_id": session_doc["user_id"],
            "session_type": session_doc["session_type"],
            "started_at": session_doc["started_at"],
            "ended_at": session_doc.get("ended_at"),
            "questions_served": session_doc.get("questions_served", []),
            "current_question_index": session_doc.get("current_question_index", 0),
            "total_questions": session_doc.get("total_questions"),
            "is_active": session_doc["is_active"],
        })

    async def record_answer(
        self, user_id: str, question_id: str, selected_answer: int
    ) -> AnswerRecord:
        """Record an answer for the current session.

        Determines correctness by comparing the selected_answer to the
        question's correct_answer_index. Tags the answer with the
        session's context (training/simulation). Advances the session
        to the next question.

        Args:
            user_id: The internal user identifier.
            question_id: The question being answered.
            selected_answer: The user's selected answer index (0-3).

        Returns:
            The persisted AnswerRecord with correctness determined.

        Raises:
            NoActiveSessionError: If no active session exists.
        """
        session_doc = await self._session_repository.get_active_session(user_id)
        if session_doc is None:
            raise NoActiveSessionError(
                f"User '{user_id}' has no active session"
            )

        # Determine correctness by fetching question
        question_doc = await self._get_question(question_id)
        is_correct = selected_answer == question_doc["correct_answer_index"]

        # Determine context from session type
        context = session_doc["session_type"]
        if context == "free_qa":
            context = "free_qa"

        # Create the answer record
        answer_record = AnswerRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            question_id=question_id,
            selected_answer=selected_answer,
            is_correct=is_correct,
            context=context,
            session_id=session_doc["id"],
            answered_at=datetime.now(timezone.utc),
        )

        answer_doc = answer_record.model_dump(mode="json")
        await self._answer_repository.create(answer_doc)

        # Advance session to next question
        session_doc["current_question_index"] = (
            session_doc.get("current_question_index", 0) + 1
        )
        await self._session_repository.update_session(session_doc)

        logger.info(
            "Recorded answer for user '%s', question '%s', correct=%s",
            user_id,
            question_id,
            is_correct,
        )

        return answer_record

    # ---- Private helpers ----

    async def _get_unanswered_questions(
        self, user_id: str, certification: str
    ) -> list[dict]:
        """Get questions not yet answered by the user.

        Args:
            user_id: The internal user identifier.
            certification: The certification filter.

        Returns:
            A list of unanswered question documents.
        """
        active_questions = (
            await self._question_repository.get_active_by_certification(certification)
        )
        answered_ids = await self._answer_repository.get_answered_question_ids(user_id)
        answered_set = set(answered_ids)

        return [q for q in active_questions if q["id"] not in answered_set]

    async def _select_simulation_questions(
        self, user_id: str, num_questions: int, certification: str
    ) -> list[str]:
        """Select questions for simulation mode proportional to domain weights.

        Distributes questions across domains according to the AI-103 exam
        weights (within ±1 question due to rounding). Falls back to
        available questions if a domain has fewer than required.

        Args:
            user_id: The internal user identifier.
            num_questions: Target number of questions.
            certification: The certification filter.

        Returns:
            A list of selected question IDs, shuffled randomly.
        """
        domain_weights = get_domain_weights()
        active_questions = (
            await self._question_repository.get_active_by_certification(certification)
        )

        # Group questions by domain
        questions_by_domain: dict[str, list[dict]] = {}
        for q in active_questions:
            domain = q.get("domain", "")
            if domain not in questions_by_domain:
                questions_by_domain[domain] = []
            questions_by_domain[domain].append(q)

        # Calculate target count per domain using largest remainder method
        target_counts = self._distribute_questions(domain_weights, num_questions)

        # Select questions from each domain
        selected_ids: list[str] = []
        for domain_type, target_count in target_counts.items():
            domain_name = domain_type.value
            available = questions_by_domain.get(domain_name, [])

            # Take up to target_count from available, randomly
            sample_size = min(target_count, len(available))
            if sample_size > 0:
                sampled = random.sample(available, sample_size)
                selected_ids.extend(q["id"] for q in sampled)

        # If we couldn't fill all slots from weighted domains, fill from any
        # remaining questions
        if len(selected_ids) < num_questions:
            all_ids = {q["id"] for q in active_questions}
            selected_set = set(selected_ids)
            remaining = [qid for qid in all_ids if qid not in selected_set]
            random.shuffle(remaining)
            needed = num_questions - len(selected_ids)
            selected_ids.extend(remaining[:needed])

        # Shuffle the final selection for random presentation order
        random.shuffle(selected_ids)

        return selected_ids

    @staticmethod
    def _distribute_questions(
        domain_weights: dict[DomainType, float], total: int
    ) -> dict[DomainType, int]:
        """Distribute N questions across domains using largest remainder method.

        Ensures each domain gets a count proportional to its weight,
        with the total equaling exactly N (±0). Rounding differences
        are resolved by giving extra questions to domains with the
        largest fractional remainders.

        Args:
            domain_weights: Mapping of domain to weight fraction.
            total: Total number of questions to distribute.

        Returns:
            Mapping of domain to question count.
        """
        # Calculate raw (fractional) allocation
        raw_allocations: dict[DomainType, float] = {}
        for domain, weight in domain_weights.items():
            raw_allocations[domain] = weight * total

        # Floor each allocation
        floored: dict[DomainType, int] = {
            domain: math.floor(raw) for domain, raw in raw_allocations.items()
        }

        # Calculate remainders
        remainders: dict[DomainType, float] = {
            domain: raw_allocations[domain] - floored[domain]
            for domain in domain_weights
        }

        # Distribute leftover using largest remainder
        leftover = total - sum(floored.values())
        sorted_by_remainder = sorted(
            remainders.keys(), key=lambda d: remainders[d], reverse=True
        )

        for i in range(leftover):
            floored[sorted_by_remainder[i]] += 1

        return floored

    async def _get_question(self, question_id: str) -> dict:
        """Fetch a question document by ID.

        Searches across all certifications since we may not know the
        partition key ahead of time.

        Args:
            question_id: The question ID.

        Returns:
            The question document.

        Raises:
            ValueError: If the question is not found.
        """
        # Try the default certification first
        doc = await self._question_repository.get_by_id(
            question_id, partition_key=DEFAULT_CERTIFICATION
        )
        if doc is not None:
            return doc

        raise ValueError(f"Question '{question_id}' not found")

    async def _build_simulation_summary(
        self, user_id: str, session_id: str
    ) -> dict:
        """Build a performance summary for a completed simulation.

        Args:
            user_id: The internal user identifier.
            session_id: The simulation session ID.

        Returns:
            A dict containing:
                - score: number of correct answers
                - total: total questions answered
                - percentage: score as percentage
                - per_domain: dict of domain → {correct, total, percentage}
        """
        # Get all answers for this session
        all_answers = await self._answer_repository.get_by_user(user_id)
        session_answers = [
            a for a in all_answers if a.get("session_id") == session_id
        ]

        total = len(session_answers)
        correct = sum(1 for a in session_answers if a.get("is_correct", False))
        percentage = (correct / total * 100) if total > 0 else 0.0

        # Per-domain breakdown
        per_domain: dict[str, dict] = {}
        for answer in session_answers:
            question_id = answer["question_id"]
            try:
                question = await self._get_question(question_id)
                domain = question.get("domain", "Unknown")
            except ValueError:
                domain = "Unknown"

            if domain not in per_domain:
                per_domain[domain] = {"correct": 0, "total": 0}

            per_domain[domain]["total"] += 1
            if answer.get("is_correct", False):
                per_domain[domain]["correct"] += 1

        # Calculate percentages per domain
        for domain_data in per_domain.values():
            domain_total = domain_data["total"]
            domain_correct = domain_data["correct"]
            domain_data["percentage"] = (
                (domain_correct / domain_total * 100) if domain_total > 0 else 0.0
            )

        return {
            "session_id": session_id,
            "score": correct,
            "total": total,
            "percentage": percentage,
            "per_domain": per_domain,
        }
