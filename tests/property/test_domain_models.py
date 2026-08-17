"""
Property-based tests for domain model serialization round-trips.

Validates: Requirements 2.2, 2.3, 3.4, 13.2, 13.3, 13.4, 13.5
"""

from datetime import datetime, timezone

import hypothesis.strategies as st
from hypothesis import given

from src.api.domain.models.answer_record import AnswerRecord
from src.api.domain.models.feedback_record import FeedbackRecord
from src.api.domain.models.question import Question
from src.api.domain.models.user import User


# --- Strategies ---

uuid_strategy = st.uuids().map(str)

aware_datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 1, 1),
    timezones=st.just(timezone.utc),
)

short_text_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=200,
)

option_text_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=100,
)

question_strategy = st.builds(
    Question,
    id=uuid_strategy,
    certification=st.sampled_from(["AI-103", "AZ-900", "DP-100"]),
    domain=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
        min_size=1,
        max_size=50,
    ),
    text=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
        min_size=10,
        max_size=500,
    ),
    options=st.lists(option_text_strategy, min_size=4, max_size=4),
    correct_answer_index=st.integers(min_value=0, max_value=3),
    short_explanation=short_text_strategy,
    detailed_explanation=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
        min_size=1,
        max_size=1000,
    ),
    created_at=aware_datetime_strategy,
    quality_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    is_active=st.booleans(),
    generated_by=st.sampled_from(["seed", "generator_agent"]),
)

user_strategy = st.builds(
    User,
    id=uuid_strategy,
    telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
    registered_at=aware_datetime_strategy,
    reminders_enabled=st.booleans(),
    last_interaction_at=st.one_of(st.none(), aware_datetime_strategy),
)

answer_record_strategy = st.builds(
    AnswerRecord,
    id=uuid_strategy,
    user_id=uuid_strategy,
    question_id=uuid_strategy,
    selected_answer=st.integers(min_value=0, max_value=3),
    is_correct=st.booleans(),
    context=st.sampled_from(["training", "simulation"]),
    session_id=uuid_strategy,
    answered_at=aware_datetime_strategy,
)

feedback_record_strategy = st.builds(
    FeedbackRecord,
    id=uuid_strategy,
    user_id=uuid_strategy,
    question_id=uuid_strategy,
    rating=st.sampled_from(["positive", "negative"]),
    flag_type=st.one_of(
        st.none(),
        st.sampled_from(
            ["incorrect_answer", "ambiguous", "too_easy", "too_hard", "off_topic"]
        ),
    ),
    comment=st.one_of(
        st.none(),
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
            min_size=1,
            max_size=200,
        ),
    ),
    created_at=aware_datetime_strategy,
)


# --- Property 3: Question model validation round-trip ---


class TestQuestionRoundTrip:
    """
    Property 3: Question model validation round-trip.

    For any valid Question object, serializing to dict and deserializing back
    produces an equivalent Question with exactly 4 options, correct_answer_index
    between 0-3, and short_explanation ≤200 chars.

    **Validates: Requirements 2.2, 2.3, 3.4, 13.3**
    """

    @given(question=question_strategy)
    def test_question_serialize_deserialize_round_trip(self, question: Question):
        """Serialize to dict and deserialize back produces equivalent object."""
        serialized = question.model_dump(mode="json")
        deserialized = Question.model_validate(serialized)
        assert deserialized == question

    @given(question=question_strategy)
    def test_question_has_exactly_4_options_after_round_trip(self, question: Question):
        """After round-trip, Question has exactly 4 options."""
        serialized = question.model_dump(mode="json")
        deserialized = Question.model_validate(serialized)
        assert len(deserialized.options) == 4

    @given(question=question_strategy)
    def test_question_correct_answer_index_in_range_after_round_trip(
        self, question: Question
    ):
        """After round-trip, correct_answer_index is between 0 and 3."""
        serialized = question.model_dump(mode="json")
        deserialized = Question.model_validate(serialized)
        assert 0 <= deserialized.correct_answer_index <= 3

    @given(question=question_strategy)
    def test_question_short_explanation_length_after_round_trip(
        self, question: Question
    ):
        """After round-trip, short_explanation is at most 200 characters."""
        serialized = question.model_dump(mode="json")
        deserialized = Question.model_validate(serialized)
        assert len(deserialized.short_explanation) <= 200


# --- Property 18: Data model serialization round-trip ---


class TestDataModelRoundTrip:
    """
    Property 18: Data model serialization round-trip.

    For any valid domain model (User, AnswerRecord, FeedbackRecord),
    serializing to dict and deserializing back produces an equivalent object
    with all fields preserved.

    **Validates: Requirements 13.2, 13.4, 13.5**
    """

    @given(user=user_strategy)
    def test_user_serialize_deserialize_round_trip(self, user: User):
        """User round-trip preserves all fields."""
        serialized = user.model_dump(mode="json")
        deserialized = User.model_validate(serialized)
        assert deserialized == user

    @given(user=user_strategy)
    def test_user_fields_preserved_after_round_trip(self, user: User):
        """User retains id, telegram_id, registered_at after round-trip."""
        serialized = user.model_dump(mode="json")
        deserialized = User.model_validate(serialized)
        assert deserialized.id == user.id
        assert deserialized.telegram_id == user.telegram_id
        assert deserialized.registered_at == user.registered_at
        assert deserialized.reminders_enabled == user.reminders_enabled
        assert deserialized.last_interaction_at == user.last_interaction_at

    @given(answer=answer_record_strategy)
    def test_answer_record_serialize_deserialize_round_trip(
        self, answer: AnswerRecord
    ):
        """AnswerRecord round-trip preserves all fields."""
        serialized = answer.model_dump(mode="json")
        deserialized = AnswerRecord.model_validate(serialized)
        assert deserialized == answer

    @given(answer=answer_record_strategy)
    def test_answer_record_fields_preserved_after_round_trip(
        self, answer: AnswerRecord
    ):
        """AnswerRecord retains all critical fields after round-trip."""
        serialized = answer.model_dump(mode="json")
        deserialized = AnswerRecord.model_validate(serialized)
        assert deserialized.id == answer.id
        assert deserialized.user_id == answer.user_id
        assert deserialized.question_id == answer.question_id
        assert deserialized.selected_answer == answer.selected_answer
        assert deserialized.is_correct == answer.is_correct
        assert deserialized.context == answer.context
        assert deserialized.session_id == answer.session_id
        assert deserialized.answered_at == answer.answered_at

    @given(feedback=feedback_record_strategy)
    def test_feedback_record_serialize_deserialize_round_trip(
        self, feedback: FeedbackRecord
    ):
        """FeedbackRecord round-trip preserves all fields."""
        serialized = feedback.model_dump(mode="json")
        deserialized = FeedbackRecord.model_validate(serialized)
        assert deserialized == feedback

    @given(feedback=feedback_record_strategy)
    def test_feedback_record_fields_preserved_after_round_trip(
        self, feedback: FeedbackRecord
    ):
        """FeedbackRecord retains all critical fields after round-trip."""
        serialized = feedback.model_dump(mode="json")
        deserialized = FeedbackRecord.model_validate(serialized)
        assert deserialized.id == feedback.id
        assert deserialized.user_id == feedback.user_id
        assert deserialized.question_id == feedback.question_id
        assert deserialized.rating == feedback.rating
        assert deserialized.flag_type == feedback.flag_type
        assert deserialized.comment == feedback.comment
        assert deserialized.created_at == feedback.created_at
