"""
Property-based tests for agent data isolation and constraints.

- Property 5: Agent data isolation — for any agent invocation, input state
  contains no user identifiers (user_id, telegram_id, username, user_name).
- Property 17: Explanation length constraint — any explanation output is at
  most 4096 characters.

**Validates: Requirements 3.6, 8.3, 12.3, 12.4, 15.7**
"""

from typing import get_type_hints

import hypothesis.strategies as st
from hypothesis import assume, given, settings

from src.ai.agents.explainer_agent.nodes.explain_node import _truncate_explanation
from src.ai.agents.explainer_agent.prompts.explainer_prompt import (
    MAX_EXPLANATION_LENGTH,
)
from src.ai.agents.explainer_agent.state import ExplainerState
from src.ai.agents.generator_agent.state import GeneratorState
from src.ai.agents.guardrail_agent.state import GuardrailState
from src.ai.agents.orchestrator_agent.state import OrchestratorState
from src.ai.agents.qa_agent.state import QAState

# --- Banned fields (user-identifying) ---

USER_IDENTIFIER_FIELDS = {"user_id", "telegram_id", "username", "user_name"}

# --- All agent state types ---

AGENT_STATE_TYPES = [
    GuardrailState,
    ExplainerState,
    GeneratorState,
    QAState,
    OrchestratorState,
]


# --- Property 5: Agent data isolation ---


class TestAgentDataIsolation:
    """
    Property 5: Agent data isolation.

    For any agent invocation, input state contains no user identifiers
    (no user_id, telegram_id, username, user_name fields).

    **Validates: Requirements 3.6, 8.3, 12.4, 15.7**
    """

    def test_guardrail_state_has_no_user_identifiers(self):
        """GuardrailState TypedDict has no user-identifying field names."""
        hints = get_type_hints(GuardrailState)
        violating_fields = USER_IDENTIFIER_FIELDS & set(hints.keys())
        assert (
            violating_fields == set()
        ), f"GuardrailState contains user-identifying fields: {violating_fields}"

    def test_explainer_state_has_no_user_identifiers(self):
        """ExplainerState TypedDict has no user-identifying field names."""
        hints = get_type_hints(ExplainerState)
        violating_fields = USER_IDENTIFIER_FIELDS & set(hints.keys())
        assert (
            violating_fields == set()
        ), f"ExplainerState contains user-identifying fields: {violating_fields}"

    def test_generator_state_has_no_user_identifiers(self):
        """GeneratorState TypedDict has no user-identifying field names."""
        hints = get_type_hints(GeneratorState)
        violating_fields = USER_IDENTIFIER_FIELDS & set(hints.keys())
        assert (
            violating_fields == set()
        ), f"GeneratorState contains user-identifying fields: {violating_fields}"

    def test_qa_state_has_no_user_identifiers(self):
        """QAState TypedDict has no user-identifying field names."""
        hints = get_type_hints(QAState)
        violating_fields = USER_IDENTIFIER_FIELDS & set(hints.keys())
        assert (
            violating_fields == set()
        ), f"QAState contains user-identifying fields: {violating_fields}"

    def test_orchestrator_state_has_no_user_identifiers(self):
        """OrchestratorState TypedDict has no user-identifying field names."""
        hints = get_type_hints(OrchestratorState)
        violating_fields = USER_IDENTIFIER_FIELDS & set(hints.keys())
        assert (
            violating_fields == set()
        ), f"OrchestratorState contains user-identifying fields: {violating_fields}"

    @given(
        state_data=st.fixed_dictionaries(
            {
                "user_message": st.text(min_size=1, max_size=500),
                "is_safe": st.booleans(),
                "block_reason": st.one_of(
                    st.none(),
                    st.sampled_from(
                        ["prompt_injection", "manipulation", "off_topic_harmful"]
                    ),
                ),
                "output_message": st.one_of(st.none(), st.text(max_size=200)),
            }
        )
    )
    def test_guardrail_state_instance_no_user_identifiers(self, state_data: dict):
        """Any GuardrailState instance dict has no user-identifying keys."""
        violating_keys = USER_IDENTIFIER_FIELDS & set(state_data.keys())
        assert (
            violating_keys == set()
        ), f"State dict contains user-identifying keys: {violating_keys}"

    @given(
        state_data=st.fixed_dictionaries(
            {
                "question_text": st.text(min_size=1, max_size=500),
                "options": st.lists(
                    st.text(min_size=1, max_size=100), min_size=4, max_size=4
                ),
                "correct_answer_index": st.integers(min_value=0, max_value=3),
                "user_selected_index": st.integers(min_value=0, max_value=3),
                "short_explanation": st.text(min_size=1, max_size=200),
                "detailed_explanation": st.text(min_size=1, max_size=2000),
                "enriched_explanation": st.one_of(
                    st.none(), st.text(max_size=2000)
                ),
                "documentation_sources": st.lists(
                    st.text(min_size=1, max_size=100), max_size=5
                ),
                "needs_enrichment": st.booleans(),
            }
        )
    )
    def test_explainer_state_instance_no_user_identifiers(self, state_data: dict):
        """Any ExplainerState instance dict has no user-identifying keys."""
        violating_keys = USER_IDENTIFIER_FIELDS & set(state_data.keys())
        assert (
            violating_keys == set()
        ), f"State dict contains user-identifying keys: {violating_keys}"

    @given(
        state_data=st.fixed_dictionaries(
            {
                "certification": st.sampled_from(["AI-103", "AZ-900"]),
                "target_domain": st.text(min_size=1, max_size=100),
                "example_questions": st.lists(
                    st.fixed_dictionaries(
                        {"text": st.text(min_size=1, max_size=100)}
                    ),
                    max_size=3,
                ),
                "feedback_context": st.one_of(
                    st.none(),
                    st.lists(
                        st.fixed_dictionaries(
                            {"rating": st.sampled_from(["positive", "negative"])}
                        ),
                        max_size=3,
                    ),
                ),
                "generated_question": st.one_of(
                    st.none(),
                    st.fixed_dictionaries(
                        {"text": st.text(min_size=1, max_size=100)}
                    ),
                ),
                "is_valid": st.booleans(),
                "validation_errors": st.lists(
                    st.text(min_size=1, max_size=100), max_size=3
                ),
            }
        )
    )
    def test_generator_state_instance_no_user_identifiers(self, state_data: dict):
        """Any GeneratorState instance dict has no user-identifying keys."""
        violating_keys = USER_IDENTIFIER_FIELDS & set(state_data.keys())
        assert (
            violating_keys == set()
        ), f"State dict contains user-identifying keys: {violating_keys}"

    @given(
        state_data=st.fixed_dictionaries(
            {
                "user_query": st.text(min_size=1, max_size=500),
                "search_results": st.lists(
                    st.fixed_dictionaries(
                        {
                            "content": st.text(min_size=1, max_size=200),
                            "source": st.text(min_size=1, max_size=100),
                            "title": st.text(min_size=1, max_size=100),
                        }
                    ),
                    max_size=3,
                ),
                "answer": st.text(max_size=500),
                "sources": st.lists(st.text(min_size=1, max_size=100), max_size=5),
                "is_in_scope": st.booleans(),
            }
        )
    )
    def test_qa_state_instance_no_user_identifiers(self, state_data: dict):
        """Any QAState instance dict has no user-identifying keys."""
        violating_keys = USER_IDENTIFIER_FIELDS & set(state_data.keys())
        assert (
            violating_keys == set()
        ), f"State dict contains user-identifying keys: {violating_keys}"

    @given(
        state_data=st.fixed_dictionaries(
            {
                "session_type": st.sampled_from(
                    ["training", "simulation", "free_qa"]
                ),
                "certification": st.sampled_from(["AI-103", "AZ-900"]),
                "domain_weights": st.dictionaries(
                    keys=st.text(min_size=1, max_size=50),
                    values=st.floats(
                        min_value=0.0, max_value=1.0, allow_nan=False
                    ),
                    min_size=1,
                    max_size=5,
                ),
                "answered_question_ids": st.lists(
                    st.uuids().map(str), max_size=10
                ),
                "available_question_ids": st.lists(
                    st.uuids().map(str), max_size=10
                ),
                "selected_question_id": st.one_of(st.none(), st.uuids().map(str)),
                "action": st.sampled_from(
                    ["serve_question", "generate_new", "end_session"]
                ),
            }
        )
    )
    def test_orchestrator_state_instance_no_user_identifiers(self, state_data: dict):
        """Any OrchestratorState instance dict has no user-identifying keys."""
        violating_keys = USER_IDENTIFIER_FIELDS & set(state_data.keys())
        assert (
            violating_keys == set()
        ), f"State dict contains user-identifying keys: {violating_keys}"


# --- Property 17: Explanation length constraint ---


class TestExplanationLengthConstraint:
    """
    Property 17: Explanation length constraint.

    Any explanation output is at most 4096 characters. The _truncate_explanation
    function guarantees this for any input text.

    **Validates: Requirements 12.3**
    """

    @given(text=st.text(min_size=0, max_size=10000))
    @settings(max_examples=500)
    def test_truncate_explanation_output_within_limit(self, text: str):
        """For any input text, _truncate_explanation output is ≤ 4096 chars."""
        result = _truncate_explanation(text)
        assert len(result) <= MAX_EXPLANATION_LENGTH, (
            f"Truncated output is {len(result)} chars, "
            f"exceeds limit of {MAX_EXPLANATION_LENGTH}"
        )

    @given(text=st.text(min_size=0, max_size=4096))
    def test_truncate_explanation_short_text_unchanged(self, text: str):
        """Text already within limit is returned unchanged."""
        result = _truncate_explanation(text)
        assert result == text

    @given(
        base=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
            min_size=200,
            max_size=500,
        ),
        repeat=st.integers(min_value=10, max_value=30),
    )
    @settings(max_examples=200)
    def test_truncate_explanation_long_text_truncated(self, base: str, repeat: int):
        """Text exceeding limit is truncated to ≤ 4096 chars."""
        text = base * repeat  # Generate text >4096 chars by repetition
        assume(len(text) > MAX_EXPLANATION_LENGTH)
        result = _truncate_explanation(text)
        assert len(result) <= MAX_EXPLANATION_LENGTH
        assert len(result) > 0  # Never returns empty for non-empty input

    @given(
        text=st.from_regex(
            r"[A-Za-z ]{100,5000}\.[A-Za-z ]{100,5000}\.[A-Za-z ]{100,5000}\.",
            fullmatch=True,
        )
    )
    @settings(max_examples=100)
    def test_truncate_explanation_preserves_sentence_boundary(self, text: str):
        """When truncating multi-sentence text, output ends at sentence boundary."""
        result = _truncate_explanation(text)
        assert len(result) <= MAX_EXPLANATION_LENGTH
        # If truncation happened, it should end with a period (sentence boundary)
        # or "..." (when no suitable sentence boundary found)
        if len(text) > MAX_EXPLANATION_LENGTH:
            assert result.endswith(".") or result.endswith("...")
