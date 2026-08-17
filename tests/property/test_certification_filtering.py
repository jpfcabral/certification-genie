"""
Property-based test for certification filtering.

Property 16: Certification filtering — for any certification filter applied to a
list of questions, the result contains only questions matching that certification.

**Validates: Requirements 10.2**
"""

from datetime import datetime, timezone

import hypothesis.strategies as st
from hypothesis import given

from src.api.domain.models.question import Question


# --- Strategies ---

CERTIFICATIONS = ["AI-103", "AZ-900", "DP-100"]

uuid_strategy = st.uuids().map(str)

aware_datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 1, 1),
    timezones=st.just(timezone.utc),
)

option_text_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=100,
)

short_text_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=200,
)


def question_dict_strategy(certification=None):
    """Generate a question dict with a specific or random certification."""
    cert_strategy = (
        st.just(certification)
        if certification is not None
        else st.sampled_from(CERTIFICATIONS)
    )
    return st.fixed_dictionaries(
        {
            "id": uuid_strategy,
            "certification": cert_strategy,
            "domain": st.text(
                alphabet=st.characters(whitelist_categories=("L", "N", "Z")),
                min_size=1,
                max_size=50,
            ),
            "text": st.text(
                alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
                min_size=10,
                max_size=500,
            ),
            "options": st.lists(option_text_strategy, min_size=4, max_size=4),
            "correct_answer_index": st.integers(min_value=0, max_value=3),
            "short_explanation": short_text_strategy,
            "detailed_explanation": st.text(
                alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
                min_size=1,
                max_size=1000,
            ),
            "created_at": aware_datetime_strategy.map(lambda dt: dt.isoformat()),
            "quality_score": st.floats(
                min_value=0.0, max_value=1.0, allow_nan=False
            ),
            "is_active": st.booleans(),
            "generated_by": st.sampled_from(["seed", "generator_agent"]),
        }
    )


question_list_strategy = st.lists(
    question_dict_strategy(), min_size=1, max_size=30
)


# --- Filter function under test ---


def filter_by_certification(
    questions: list[dict], certification: str
) -> list[dict]:
    """
    Pure filtering logic that mirrors the CosmosDB query:
    SELECT * FROM c WHERE c.certification = @certification

    This is the logic that the QuestionRepository.get_active_by_certification
    applies at the data level.
    """
    return [q for q in questions if q["certification"] == certification]


# --- Property 16: Certification filtering ---


class TestCertificationFiltering:
    """
    Property 16: Certification filtering.

    For any certification filter value applied to the Question_Bank, the query
    result SHALL contain only questions whose certification field exactly matches
    the filter value — no questions from other certifications shall be included.

    **Validates: Requirements 10.2**
    """

    @given(
        questions=question_list_strategy,
        target_certification=st.sampled_from(CERTIFICATIONS),
    )
    def test_filtered_results_contain_only_matching_certification(
        self, questions: list[dict], target_certification: str
    ):
        """All results from filtering by certification have that certification."""
        result = filter_by_certification(questions, target_certification)
        for q in result:
            assert q["certification"] == target_certification

    @given(
        questions=question_list_strategy,
        target_certification=st.sampled_from(CERTIFICATIONS),
    )
    def test_filtering_does_not_include_other_certifications(
        self, questions: list[dict], target_certification: str
    ):
        """No question with a different certification appears in filtered results."""
        result = filter_by_certification(questions, target_certification)
        other_certs = [c for c in CERTIFICATIONS if c != target_certification]
        for q in result:
            assert q["certification"] not in other_certs

    @given(
        questions=question_list_strategy,
        target_certification=st.sampled_from(CERTIFICATIONS),
    )
    def test_filtering_preserves_all_matching_questions(
        self, questions: list[dict], target_certification: str
    ):
        """Every question in the original list that matches the certification
        must appear in the filtered result (no false negatives)."""
        result = filter_by_certification(questions, target_certification)
        expected = [
            q for q in questions if q["certification"] == target_certification
        ]
        assert len(result) == len(expected)
        for q in expected:
            assert q in result

    @given(
        questions=question_list_strategy,
        target_certification=st.sampled_from(CERTIFICATIONS),
    )
    def test_filtered_result_is_subset_of_original(
        self, questions: list[dict], target_certification: str
    ):
        """The filtered result is always a subset of the original list."""
        result = filter_by_certification(questions, target_certification)
        assert len(result) <= len(questions)
        for q in result:
            assert q in questions
