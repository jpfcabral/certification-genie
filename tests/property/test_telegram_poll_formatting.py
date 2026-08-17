"""
Property-based tests for Telegram Poll formatting.

Property 9: For any Question model, formatting it as a Telegram Poll
produces output with type="quiz", exactly 4 option strings, is_anonymous=False,
and correct_option_id equal to the question's correct_answer_index.

**Validates: Requirements 4.2, 5.2, 14.2**
"""

from datetime import datetime, timezone

import hypothesis.strategies as st
from hypothesis import given

from src.api.domain.models.question import Question
from src.bot.formatters.question_formatter import format_question_as_poll


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


# --- Property 9: Telegram Poll formatting ---


class TestTelegramPollFormatting:
    """
    Property 9: Telegram Poll formatting.

    For any Question model, formatting it as a Telegram Poll produces output with
    type="quiz", exactly 4 option strings, is_anonymous=False, and correct_option_id
    equal to the question's correct_answer_index.

    **Validates: Requirements 4.2, 5.2, 14.2**
    """

    @given(question=question_strategy)
    def test_poll_type_is_quiz(self, question: Question):
        """Formatted poll always has type='quiz'."""
        poll = format_question_as_poll(question)
        assert poll.type == "quiz"

    @given(question=question_strategy)
    def test_poll_has_exactly_4_options(self, question: Question):
        """Formatted poll always has exactly 4 option strings."""
        poll = format_question_as_poll(question)
        assert len(poll.options) == 4
        assert all(isinstance(opt, str) for opt in poll.options)

    @given(question=question_strategy)
    def test_poll_is_not_anonymous(self, question: Question):
        """Formatted poll always has is_anonymous=False."""
        poll = format_question_as_poll(question)
        assert poll.is_anonymous is False

    @given(question=question_strategy)
    def test_poll_correct_option_id_matches_answer_index(self, question: Question):
        """Formatted poll correct_option_id equals the question's correct_answer_index."""
        poll = format_question_as_poll(question)
        assert poll.correct_option_id == question.correct_answer_index

    @given(question=question_strategy)
    def test_poll_question_text_matches(self, question: Question):
        """Formatted poll question text matches the original question text."""
        poll = format_question_as_poll(question)
        assert poll.question == question.text

    @given(question=question_strategy)
    def test_poll_options_match_question_options(self, question: Question):
        """Formatted poll options match the original question options."""
        poll = format_question_as_poll(question)
        assert poll.options == question.options
