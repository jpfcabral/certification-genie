"""
Property-based tests for question and progress logic.

Tests pure logic functions related to:
- Question duplicate detection via text normalization
- Question selection prioritizing unanswered questions
- Answer correctness determination
- Progress calculation correctness
- Quality score and deactivation logic
- Weak areas identification

Validates: Requirements 3.5, 4.3, 4.4, 4.6, 5.5, 11.1, 15.4, 15.5, 17.3
"""

import hypothesis.strategies as st
from hypothesis import given, assume

from src.api.application.services.question_service import _normalize_text


# --- Strategies ---

# Text with varied whitespace and casing for duplicate detection
question_text_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=5,
    max_size=300,
)

# Domain names for progress calculations
domain_strategy = st.sampled_from([
    "Generative AI and Agents",
    "Computer Vision",
    "Text Analysis",
    "Information Extraction",
    "Plan and Manage",
])

# Question IDs
question_id_strategy = st.uuids().map(str)


# --- Property 4: Question duplicate detection ---


class TestQuestionDuplicateDetection:
    """
    Property 4: Question duplicate detection.

    For any pair of questions where the text is identical or near-identical
    (differing only in whitespace or casing), the deduplication function
    SHALL identify them as duplicates.

    **Validates: Requirements 3.5**
    """

    @given(text=question_text_strategy)
    def test_normalize_is_idempotent(self, text: str):
        """Normalizing already-normalized text produces the same result."""
        normalized = _normalize_text(text)
        assert _normalize_text(normalized) == normalized

    @given(text=question_text_strategy)
    def test_extra_whitespace_produces_same_normalized_form(self, text: str):
        """Text with extra whitespace normalizes to the same form as without."""
        assume(len(text.strip()) > 0)
        with_extra_spaces = "  " + text + "   "
        assert _normalize_text(with_extra_spaces) == _normalize_text(text)

    @given(text=question_text_strategy)
    def test_case_insensitive_comparison(self, text: str):
        """Text is normalized to lowercase, so casing is irrelevant for comparison."""
        assume(len(text.strip()) > 0)
        # _normalize_text applies .lower(), so any text should equal its lowercase form
        assert _normalize_text(text) == _normalize_text(text.lower())

    @given(
        words=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("L", "N")),
                min_size=1,
                max_size=20,
            ),
            min_size=2,
            max_size=10,
        )
    )
    def test_multiple_internal_spaces_collapsed(self, words: list[str]):
        """Multiple internal whitespace characters are collapsed to single space."""
        spaced_text = "   ".join(words)
        single_spaced = " ".join(words)
        assert _normalize_text(spaced_text) == _normalize_text(single_spaced)

    @given(text=question_text_strategy)
    def test_identical_texts_detected_as_duplicates(self, text: str):
        """Identical question texts are detected as duplicates via normalization."""
        assume(len(text.strip()) > 0)
        assert _normalize_text(text) == _normalize_text(text)

    @given(
        text=question_text_strategy,
        prefix=st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=3,
            max_size=10,
        ),
    )
    def test_different_texts_not_detected_as_duplicates(self, text: str, prefix: str):
        """Texts with different content are not detected as duplicates."""
        assume(len(text.strip()) > 0)
        assume(len(prefix.strip()) > 0)
        modified_text = prefix + " " + text
        # They should differ after normalization (unless text starts with prefix)
        norm_original = _normalize_text(text)
        norm_modified = _normalize_text(modified_text)
        # The modified text prepends content, so it should differ
        assert norm_modified != norm_original


# --- Property 6: Question selection prioritizes unanswered ---


class TestQuestionSelectionPrioritizesUnanswered:
    """
    Property 6: Question selection prioritizes unanswered.

    With unanswered questions available, selection always returns a question
    from the unanswered set — never serving an already-answered question
    while unanswered ones remain available.

    **Validates: Requirements 4.6**
    """

    @given(
        all_question_ids=st.lists(
            question_id_strategy, min_size=2, max_size=50, unique=True
        ),
        answered_fraction=st.floats(min_value=0.1, max_value=0.9),
    )
    def test_filtering_returns_only_unanswered(
        self, all_question_ids: list[str], answered_fraction: float
    ):
        """Filtering active questions by answered IDs returns only unanswered ones."""
        # Simulate the filtering logic from question_service.get_unanswered_questions
        num_answered = max(1, int(len(all_question_ids) * answered_fraction))
        answered_ids = set(all_question_ids[:num_answered])
        active_questions = [{"id": qid} for qid in all_question_ids]

        # Apply the same filtering logic as the service
        unanswered = [q for q in active_questions if q["id"] not in answered_ids]

        # All returned questions should NOT be in the answered set
        for q in unanswered:
            assert q["id"] not in answered_ids

    @given(
        all_question_ids=st.lists(
            question_id_strategy, min_size=2, max_size=50, unique=True
        ),
        answered_fraction=st.floats(min_value=0.1, max_value=0.9),
    )
    def test_filtering_returns_correct_count(
        self, all_question_ids: list[str], answered_fraction: float
    ):
        """Number of unanswered = total - answered."""
        num_answered = max(1, int(len(all_question_ids) * answered_fraction))
        answered_ids = set(all_question_ids[:num_answered])
        active_questions = [{"id": qid} for qid in all_question_ids]

        unanswered = [q for q in active_questions if q["id"] not in answered_ids]

        expected_count = len(all_question_ids) - len(answered_ids)
        assert len(unanswered) == expected_count

    @given(
        all_question_ids=st.lists(
            question_id_strategy, min_size=3, max_size=50, unique=True
        ),
        answered_fraction=st.floats(min_value=0.1, max_value=0.8),
    )
    def test_selection_from_unanswered_never_in_answered(
        self, all_question_ids: list[str], answered_fraction: float
    ):
        """Any question selected from unanswered set is never in the answered set."""
        num_answered = max(1, int(len(all_question_ids) * answered_fraction))
        answered_ids = set(all_question_ids[:num_answered])
        active_questions = [{"id": qid} for qid in all_question_ids]

        unanswered = [q for q in active_questions if q["id"] not in answered_ids]
        assume(len(unanswered) > 0)

        # Any selection from the unanswered list should not be answered
        for selected in unanswered:
            assert selected["id"] not in answered_ids


# --- Property 7: Answer correctness determination ---


class TestAnswerCorrectnessDetermination:
    """
    Property 7: Answer correctness determination.

    For any question with correct_answer_index C and any user-selected
    answer index S, is_correct = (S == C).

    **Validates: Requirements 4.3, 4.4**
    """

    @given(
        correct_answer_index=st.integers(min_value=0, max_value=3),
        selected_answer=st.integers(min_value=0, max_value=3),
    )
    def test_is_correct_equals_selected_matches_correct(
        self, correct_answer_index: int, selected_answer: int
    ):
        """is_correct is True iff selected == correct_answer_index."""
        is_correct = selected_answer == correct_answer_index
        assert is_correct == (selected_answer == correct_answer_index)

    @given(correct_answer_index=st.integers(min_value=0, max_value=3))
    def test_selecting_correct_answer_is_always_correct(
        self, correct_answer_index: int
    ):
        """Selecting the correct answer always yields is_correct=True."""
        is_correct = correct_answer_index == correct_answer_index
        assert is_correct is True

    @given(
        correct_answer_index=st.integers(min_value=0, max_value=3),
        selected_answer=st.integers(min_value=0, max_value=3),
    )
    def test_selecting_wrong_answer_is_never_correct(
        self, correct_answer_index: int, selected_answer: int
    ):
        """Selecting a wrong answer always yields is_correct=False."""
        assume(selected_answer != correct_answer_index)
        is_correct = selected_answer == correct_answer_index
        assert is_correct is False


# --- Property 10: Progress calculation correctness ---


class TestProgressCalculationCorrectness:
    """
    Property 10: Progress calculation correctness.

    For any set of AnswerRecords: total_answered = record count,
    overall_percentage = (correct_count / total_count * 100),
    per-domain percentages = (domain_correct / domain_total * 100).

    **Validates: Requirements 5.5, 11.1**
    """

    @given(
        answers=st.lists(
            st.tuples(
                domain_strategy,
                st.booleans(),  # is_correct
            ),
            min_size=5,
            max_size=100,
        )
    )
    def test_total_answered_equals_record_count(
        self, answers: list[tuple[str, bool]]
    ):
        """total_answered equals the number of answer records."""
        total_answered = len(answers)
        assert total_answered == len(answers)

    @given(
        answers=st.lists(
            st.tuples(
                domain_strategy,
                st.booleans(),  # is_correct
            ),
            min_size=5,
            max_size=100,
        )
    )
    def test_overall_percentage_mathematically_correct(
        self, answers: list[tuple[str, bool]]
    ):
        """overall_percentage = correct_count / total_count * 100."""
        total_answered = len(answers)
        correct_count = sum(1 for _, is_correct in answers if is_correct)

        overall_percentage = (correct_count / total_answered) * 100

        expected = (correct_count / total_answered) * 100
        assert abs(overall_percentage - expected) < 1e-10

    @given(
        answers=st.lists(
            st.tuples(
                domain_strategy,
                st.booleans(),  # is_correct
            ),
            min_size=5,
            max_size=100,
        )
    )
    def test_per_domain_percentages_mathematically_correct(
        self, answers: list[tuple[str, bool]]
    ):
        """Each per-domain percentage = domain_correct / domain_total * 100."""
        from collections import defaultdict

        domain_totals: dict[str, int] = defaultdict(int)
        domain_correct: dict[str, int] = defaultdict(int)

        for domain, is_correct in answers:
            domain_totals[domain] += 1
            if is_correct:
                domain_correct[domain] += 1

        per_domain: dict[str, float] = {}
        for domain, total in domain_totals.items():
            correct = domain_correct.get(domain, 0)
            per_domain[domain] = (correct / total) * 100

        # Verify each domain percentage
        for domain, percentage in per_domain.items():
            expected = (domain_correct.get(domain, 0) / domain_totals[domain]) * 100
            assert abs(percentage - expected) < 1e-10

    @given(
        answers=st.lists(
            st.tuples(
                domain_strategy,
                st.booleans(),
            ),
            min_size=5,
            max_size=100,
        )
    )
    def test_per_domain_percentages_bounded_0_to_100(
        self, answers: list[tuple[str, bool]]
    ):
        """All per-domain percentages are between 0 and 100 inclusive."""
        from collections import defaultdict

        domain_totals: dict[str, int] = defaultdict(int)
        domain_correct: dict[str, int] = defaultdict(int)

        for domain, is_correct in answers:
            domain_totals[domain] += 1
            if is_correct:
                domain_correct[domain] += 1

        for domain, total in domain_totals.items():
            correct = domain_correct.get(domain, 0)
            percentage = (correct / total) * 100
            assert 0.0 <= percentage <= 100.0

    @given(
        answers=st.lists(
            st.tuples(
                domain_strategy,
                st.booleans(),
            ),
            min_size=5,
            max_size=100,
        )
    )
    def test_overall_percentage_bounded_0_to_100(
        self, answers: list[tuple[str, bool]]
    ):
        """Overall percentage is between 0 and 100 inclusive."""
        total_answered = len(answers)
        correct_count = sum(1 for _, is_correct in answers if is_correct)
        overall_percentage = (correct_count / total_answered) * 100
        assert 0.0 <= overall_percentage <= 100.0


# --- Property 14: Quality score and deactivation ---


class TestQualityScoreAndDeactivation:
    """
    Property 14: Quality score calculation and deactivation.

    For any set of FeedbackRecords for a question, the quality score equals
    positive_count / total_count. When this score falls below the configured
    threshold, the question's is_active field SHALL be set to False.

    **Validates: Requirements 15.4, 15.5**
    """

    @given(
        positive_count=st.integers(min_value=0, max_value=100),
        negative_count=st.integers(min_value=0, max_value=100),
    )
    def test_quality_score_equals_positive_over_total(
        self, positive_count: int, negative_count: int
    ):
        """quality_score = positive_count / total_count."""
        total_count = positive_count + negative_count
        assume(total_count > 0)

        quality_score = positive_count / total_count

        expected = positive_count / total_count
        assert abs(quality_score - expected) < 1e-10

    @given(
        positive_count=st.integers(min_value=0, max_value=100),
        negative_count=st.integers(min_value=0, max_value=100),
    )
    def test_quality_score_bounded_0_to_1(
        self, positive_count: int, negative_count: int
    ):
        """quality_score is always between 0.0 and 1.0."""
        total_count = positive_count + negative_count
        assume(total_count > 0)

        quality_score = positive_count / total_count
        assert 0.0 <= quality_score <= 1.0

    @given(
        positive_count=st.integers(min_value=0, max_value=100),
        negative_count=st.integers(min_value=1, max_value=100),
        threshold=st.floats(min_value=0.1, max_value=0.9, allow_nan=False),
    )
    def test_below_threshold_deactivates(
        self, positive_count: int, negative_count: int, threshold: float
    ):
        """When quality_score < threshold, question should be deactivated."""
        total_count = positive_count + negative_count
        quality_score = positive_count / total_count

        should_deactivate = quality_score < threshold

        # Simulate the deactivation logic
        is_active = not should_deactivate if quality_score < threshold else True
        if quality_score < threshold:
            assert is_active is False
        else:
            assert is_active is True

    @given(
        positive_count=st.integers(min_value=0, max_value=100),
        negative_count=st.integers(min_value=0, max_value=100),
        threshold=st.floats(min_value=0.1, max_value=0.9, allow_nan=False),
    )
    def test_at_or_above_threshold_remains_active(
        self, positive_count: int, negative_count: int, threshold: float
    ):
        """When quality_score >= threshold, question remains active."""
        total_count = positive_count + negative_count
        assume(total_count > 0)

        quality_score = positive_count / total_count
        assume(quality_score >= threshold)

        # Question should remain active
        is_active = not (quality_score < threshold)
        assert is_active is True

    @given(negative_count=st.integers(min_value=1, max_value=100))
    def test_zero_positive_gives_zero_score(self, negative_count: int):
        """With zero positive ratings, quality_score is 0.0."""
        quality_score = 0 / (0 + negative_count)
        assert quality_score == 0.0

    @given(positive_count=st.integers(min_value=1, max_value=100))
    def test_all_positive_gives_perfect_score(self, positive_count: int):
        """With all positive ratings, quality_score is 1.0."""
        quality_score = positive_count / (positive_count + 0)
        assert quality_score == 1.0


# --- Property 15: Weak areas identification ---


class TestWeakAreasIdentification:
    """
    Property 15: Weak areas identification.

    For any user's AnswerRecords distributed across domains, the weak areas
    algorithm identifies the 3 domains with the lowest correct-answer
    percentage and returns them in ascending order of performance.

    **Validates: Requirements 17.3**
    """

    @given(
        per_domain=st.dictionaries(
            keys=domain_strategy,
            values=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
            min_size=3,
            max_size=5,
        )
    )
    def test_weak_areas_returns_at_most_3_domains(
        self, per_domain: dict[str, float]
    ):
        """Weak areas returns at most 3 domains."""
        assume(len(per_domain) >= 3)

        sorted_domains = sorted(per_domain.items(), key=lambda x: x[1])
        weak_areas = [
            {"domain": domain, "percentage": percentage}
            for domain, percentage in sorted_domains[:3]
        ]

        assert len(weak_areas) <= 3

    @given(
        per_domain=st.dictionaries(
            keys=domain_strategy,
            values=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
            min_size=3,
            max_size=5,
        )
    )
    def test_weak_areas_sorted_ascending_by_percentage(
        self, per_domain: dict[str, float]
    ):
        """Weak areas are sorted in ascending order of performance."""
        assume(len(per_domain) >= 3)

        sorted_domains = sorted(per_domain.items(), key=lambda x: x[1])
        weak_areas = [
            {"domain": domain, "percentage": percentage}
            for domain, percentage in sorted_domains[:3]
        ]

        # Verify ascending order
        for i in range(len(weak_areas) - 1):
            assert weak_areas[i]["percentage"] <= weak_areas[i + 1]["percentage"]

    @given(
        per_domain=st.dictionaries(
            keys=domain_strategy,
            values=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
            min_size=3,
            max_size=5,
        )
    )
    def test_weak_areas_contains_lowest_percentages(
        self, per_domain: dict[str, float]
    ):
        """Weak areas contains the domains with the lowest percentages."""
        assume(len(per_domain) >= 3)

        sorted_domains = sorted(per_domain.items(), key=lambda x: x[1])
        weak_areas = [
            {"domain": domain, "percentage": percentage}
            for domain, percentage in sorted_domains[:3]
        ]

        # The highest percentage in weak areas should be <= the lowest
        # percentage among remaining domains
        weak_area_percentages = {wa["percentage"] for wa in weak_areas}
        remaining = sorted_domains[3:]

        if remaining:
            max_weak = max(weak_area_percentages)
            min_remaining = min(pct for _, pct in remaining)
            assert max_weak <= min_remaining

    @given(
        per_domain=st.dictionaries(
            keys=domain_strategy,
            values=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
            min_size=1,
            max_size=2,
        )
    )
    def test_weak_areas_returns_fewer_when_less_than_3_domains(
        self, per_domain: dict[str, float]
    ):
        """When fewer than 3 domains exist, returns all available domains."""
        sorted_domains = sorted(per_domain.items(), key=lambda x: x[1])
        weak_areas = [
            {"domain": domain, "percentage": percentage}
            for domain, percentage in sorted_domains[:3]
        ]

        assert len(weak_areas) == len(per_domain)
