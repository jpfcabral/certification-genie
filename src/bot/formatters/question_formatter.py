from dataclasses import dataclass

from src.api.domain.models.question import Question


@dataclass
class TelegramPollParams:
    """Parameters for sending a Telegram quiz poll."""

    question: str
    options: list[str]
    type: str
    correct_option_id: int
    is_anonymous: bool


def format_question_as_poll(question: Question) -> TelegramPollParams:
    """Format a Question model as Telegram Poll parameters (quiz mode, non-anonymous, 4 options).

    Assumes question text ≤300 chars and options ≤100 chars (enforced at generation/validation).
    """
    return TelegramPollParams(
        question=question.text,
        options=question.options,
        type="quiz",
        correct_option_id=question.correct_answer_index,
        is_anonymous=False,
    )
