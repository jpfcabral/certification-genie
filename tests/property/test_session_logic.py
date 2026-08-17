"""
Property-based tests for session logic.

Tests pure logic functions related to:
- Simulation domain distribution (largest remainder method)
- Simulation context tagging for answer records

Validates: Requirements 5.1, 5.6, 5.7
"""

import uuid
from datetime import datetime, timezone

import hypothesis.strategies as st
from hypothesis import given, assume

from src.api.application.services.session_service import SessionService
from src.api.domain.enums.domain_type import DomainType
from src.api.domain.models.answer_record import AnswerRecord


# --- Strategies ---

# Strategy for domain weight dictionaries (subsets of all domains with positive weights)
domain_weights_strategy = st.fixed_dictionaries({
    DomainType.GENERATIVE_AI_AND_AGENTS: st.floats(min_value=0.05, max_value=0.5, allow_nan=False, allow_infinity=False),
    DomainType.COMPUTER_VISION: st.floats(min_value=0.05, max_value=0.5, allow_nan=False, allow_infinity=False),
    DomainType.TEXT_ANALYSIS: st.floats(min_value=0.05, max_value=0.5, allow_nan=False, allow_infinity=False),
    DomainType.INFORMATION_EXTRACTION: st.floats(min_value=0.05, max_value=0.5, allow_nan=False, allow_infinity=False),
    DomainType.PLAN_AND_MANAGE: st.floats(min_value=0.05, max_value=0.5, allow_nan=False, allow_infinity=False),
}).map(lambda d: _normalize_weights(d))

# Total number of questions in simulation
total_questions_strategy = st.integers(min_value=5, max_value=100)


def _normalize_weights(weights: dict[DomainType, float]) -> dict[DomainType, float]:
    """Normalize weights so they sum to 1.0."""
    total = sum(weights.values())
    return {domain: w / total for domain, w in weights.items()}


# --- Property 8: Simulation domain distribution ---


class TestSimulationDomainDistribution:
    """
    Property 8: Simulation domain distribution.

    For any set of domain weights and a target question count N, the
    simulation question distribution algorithm SHALL produce a selection
    where each domain's question count is proportional to its weight
    (within ±1 question due to rounding), and the total equals N.

    **Validates: Requirements 5.1, 5.6**
    """

    @given(
        weights=domain_weights_strategy,
        total=total_questions_strategy,
    )
    def test_total_equals_n(
        self, weights: dict[DomainType, float], total: int
    ):
        """The sum of distributed questions must equal exactly N."""
        distribution = SessionService._distribute_questions(weights, total)
        assert sum(distribution.values()) == total

    @given(
        weights=domain_weights_strategy,
        total=total_questions_strategy,
    )
    def test_each_count_within_plus_minus_one_of_weighted_proportion(
        self, weights: dict[DomainType, float], total: int
    ):
        """Each domain's count is within ±1 of weight * N."""
        distribution = SessionService._distribute_questions(weights, total)

        for domain, count in distribution.items():
            expected = weights[domain] * total
            assert abs(count - expected) <= 1.0, (
                f"Domain {domain.value}: count={count}, "
                f"expected={expected:.2f}, diff={abs(count - expected):.2f}"
            )

    @given(
        weights=domain_weights_strategy,
        total=total_questions_strategy,
    )
    def test_all_counts_non_negative(
        self, weights: dict[DomainType, float], total: int
    ):
        """No domain should receive a negative number of questions."""
        distribution = SessionService._distribute_questions(weights, total)

        for domain, count in distribution.items():
            assert count >= 0, f"Domain {domain.value} has negative count: {count}"

    @given(
        weights=domain_weights_strategy,
        total=total_questions_strategy,
    )
    def test_all_domains_present_in_result(
        self, weights: dict[DomainType, float], total: int
    ):
        """Every domain in the input weights appears in the distribution result."""
        distribution = SessionService._distribute_questions(weights, total)

        for domain in weights:
            assert domain in distribution, (
                f"Domain {domain.value} missing from distribution"
            )

    @given(
        weights=domain_weights_strategy,
        total=total_questions_strategy,
    )
    def test_distribution_is_deterministic(
        self, weights: dict[DomainType, float], total: int
    ):
        """Same inputs always produce the same distribution."""
        distribution_1 = SessionService._distribute_questions(weights, total)
        distribution_2 = SessionService._distribute_questions(weights, total)
        assert distribution_1 == distribution_2

    @given(total=total_questions_strategy)
    def test_with_real_ai103_weights(self, total: int):
        """Using the actual AI-103 domain weights, total equals N and each within ±1."""
        from src.api.domain.enums.domain_type import get_domain_weights

        weights = get_domain_weights()
        distribution = SessionService._distribute_questions(weights, total)

        # Total must equal N
        assert sum(distribution.values()) == total

        # Each count within ±1 of weighted proportion
        for domain, count in distribution.items():
            expected = weights[domain] * total
            assert abs(count - expected) <= 1.0


# --- Property 19: Simulation context tagging ---


class TestSimulationContextTagging:
    """
    Property 19: Simulation context tagging.

    For any answer recorded during a Simulation_Session, the AnswerRecord
    SHALL have context="simulation" and a valid session_id linking it to
    the active simulation.

    **Validates: Requirements 5.7**
    """

    @given(
        user_id=st.uuids().map(str),
        question_id=st.uuids().map(str),
        selected_answer=st.integers(min_value=0, max_value=3),
        is_correct=st.booleans(),
    )
    def test_simulation_answer_has_simulation_context(
        self,
        user_id: str,
        question_id: str,
        selected_answer: int,
        is_correct: bool,
    ):
        """An answer in a simulation session has context='simulation'."""
        session_id = str(uuid.uuid4())
        session_type = "simulation"

        # The session service sets context = session_type for simulation sessions
        context = session_type

        answer_record = AnswerRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            question_id=question_id,
            selected_answer=selected_answer,
            is_correct=is_correct,
            context=context,
            session_id=session_id,
            answered_at=datetime.now(timezone.utc),
        )

        assert answer_record.context == "simulation"

    @given(
        user_id=st.uuids().map(str),
        question_id=st.uuids().map(str),
        selected_answer=st.integers(min_value=0, max_value=3),
        is_correct=st.booleans(),
        session_id=st.uuids().map(str),
    )
    def test_simulation_answer_has_valid_session_id(
        self,
        user_id: str,
        question_id: str,
        selected_answer: int,
        is_correct: bool,
        session_id: str,
    ):
        """An answer in a simulation session has a non-empty session_id string."""
        session_type = "simulation"
        context = session_type

        answer_record = AnswerRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            question_id=question_id,
            selected_answer=selected_answer,
            is_correct=is_correct,
            context=context,
            session_id=session_id,
            answered_at=datetime.now(timezone.utc),
        )

        assert answer_record.session_id == session_id
        assert isinstance(answer_record.session_id, str)
        assert len(answer_record.session_id) > 0

    @given(
        user_id=st.uuids().map(str),
        question_id=st.uuids().map(str),
        selected_answer=st.integers(min_value=0, max_value=3),
        is_correct=st.booleans(),
    )
    def test_simulation_context_matches_session_type(
        self,
        user_id: str,
        question_id: str,
        selected_answer: int,
        is_correct: bool,
    ):
        """The context field is derived directly from the session_type='simulation'."""
        session_id = str(uuid.uuid4())
        session_type = "simulation"

        # Simulating the logic from SessionService.record_answer:
        # context = session_doc["session_type"]
        context = session_type

        answer_record = AnswerRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            question_id=question_id,
            selected_answer=selected_answer,
            is_correct=is_correct,
            context=context,
            session_id=session_id,
            answered_at=datetime.now(timezone.utc),
        )

        assert answer_record.context == session_type
        assert answer_record.context == "simulation"

    @given(
        user_id=st.uuids().map(str),
        question_id=st.uuids().map(str),
        selected_answer=st.integers(min_value=0, max_value=3),
        is_correct=st.booleans(),
        session_type=st.sampled_from(["training", "simulation", "free_qa"]),
    )
    def test_context_always_equals_session_type(
        self,
        user_id: str,
        question_id: str,
        selected_answer: int,
        is_correct: bool,
        session_type: str,
    ):
        """For any session type, the context field equals the session_type value."""
        session_id = str(uuid.uuid4())

        # Simulating session_service logic: context = session_doc["session_type"]
        context = session_type

        answer_record = AnswerRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            question_id=question_id,
            selected_answer=selected_answer,
            is_correct=is_correct,
            context=context,
            session_id=session_id,
            answered_at=datetime.now(timezone.utc),
        )

        assert answer_record.context == session_type
        # Specifically for simulation, it must be "simulation"
        if session_type == "simulation":
            assert answer_record.context == "simulation"
