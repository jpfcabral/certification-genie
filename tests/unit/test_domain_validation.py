"""Unit tests for domain model validation.

Validates: Requirements 2.2, 2.3, 1.4
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.api.domain.models import Question, FeedbackRecord, User


# --- Helpers ---

def _valid_question_kwargs() -> dict:
    """Returns valid kwargs for constructing a Question."""
    return {
        "id": "q-001",
        "certification": "AI-103",
        "domain": "Generative AI and Agents",
        "text": "Which service provides multi-turn conversational AI?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer_index": 1,
        "short_explanation": "Short explanation here.",
        "detailed_explanation": "Detailed explanation of the correct answer.",
        "created_at": datetime(2024, 1, 1),
    }


def _valid_feedback_kwargs() -> dict:
    """Returns valid kwargs for constructing a FeedbackRecord."""
    return {
        "id": "fb-001",
        "user_id": "user-001",
        "question_id": "q-001",
        "rating": "positive",
        "created_at": datetime(2024, 1, 1),
    }


# --- Question: options must have exactly 4 items ---

class TestQuestionOptionsValidation:
    def test_rejects_fewer_than_4_options(self):
        kwargs = _valid_question_kwargs()
        kwargs["options"] = ["A", "B", "C"]
        with pytest.raises(ValidationError, match="exactly 4 options"):
            Question(**kwargs)

    def test_rejects_more_than_4_options(self):
        kwargs = _valid_question_kwargs()
        kwargs["options"] = ["A", "B", "C", "D", "E"]
        with pytest.raises(ValidationError, match="exactly 4 options"):
            Question(**kwargs)

    def test_rejects_empty_options(self):
        kwargs = _valid_question_kwargs()
        kwargs["options"] = []
        with pytest.raises(ValidationError, match="exactly 4 options"):
            Question(**kwargs)


# --- Question: correct_answer_index must be 0-3 ---

class TestQuestionAnswerIndexValidation:
    def test_rejects_negative_index(self):
        kwargs = _valid_question_kwargs()
        kwargs["correct_answer_index"] = -1
        with pytest.raises(ValidationError, match="must be between 0 and 3"):
            Question(**kwargs)

    def test_rejects_index_above_3(self):
        kwargs = _valid_question_kwargs()
        kwargs["correct_answer_index"] = 4
        with pytest.raises(ValidationError, match="must be between 0 and 3"):
            Question(**kwargs)


# --- Question: short_explanation must be <= 200 characters ---

class TestQuestionShortExplanationValidation:
    def test_rejects_explanation_over_200_chars(self):
        kwargs = _valid_question_kwargs()
        kwargs["short_explanation"] = "x" * 201
        with pytest.raises(ValidationError, match="at most 200 characters"):
            Question(**kwargs)

    def test_accepts_explanation_at_exactly_200_chars(self):
        kwargs = _valid_question_kwargs()
        kwargs["short_explanation"] = "x" * 200
        q = Question(**kwargs)
        assert len(q.short_explanation) == 200


# --- FeedbackRecord: comment must be <= 200 characters ---

class TestFeedbackRecordCommentValidation:
    def test_rejects_comment_over_200_chars(self):
        kwargs = _valid_feedback_kwargs()
        kwargs["comment"] = "x" * 201
        with pytest.raises(ValidationError, match="at most 200 characters"):
            FeedbackRecord(**kwargs)

    def test_accepts_comment_at_exactly_200_chars(self):
        kwargs = _valid_feedback_kwargs()
        kwargs["comment"] = "x" * 200
        fb = FeedbackRecord(**kwargs)
        assert len(fb.comment) == 200

    def test_accepts_none_comment(self):
        kwargs = _valid_feedback_kwargs()
        kwargs["comment"] = None
        fb = FeedbackRecord(**kwargs)
        assert fb.comment is None


# --- User: accepts minimal valid data ---

class TestUserMinimalData:
    def test_accepts_only_required_fields(self):
        user = User(
            id="user-uuid-001",
            telegram_id=123456789,
            registered_at=datetime(2024, 1, 1),
        )
        assert user.id == "user-uuid-001"
        assert user.telegram_id == 123456789
        assert user.registered_at == datetime(2024, 1, 1)
        # Defaults
        assert user.reminders_enabled is True
        assert user.last_interaction_at is None
