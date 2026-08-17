from telegram import InlineKeyboardButton, InlineKeyboardMarkup


FLAG_SUBCATEGORIES = [
    ("Incorrect answer", "flag:incorrect_answer"),
    ("Ambiguous wording", "flag:ambiguous"),
    ("Too easy", "flag:too_easy"),
    ("Too hard", "flag:too_hard"),
    ("Off-topic", "flag:off_topic"),
]


def build_feedback_buttons(question_id: str) -> InlineKeyboardMarkup:
    """Build feedback buttons with thumbs up, thumbs down, and flag."""
    keyboard = [
        [
            InlineKeyboardButton("👍", callback_data=f"feedback:positive:{question_id}"),
            InlineKeyboardButton("👎", callback_data=f"feedback:negative:{question_id}"),
            InlineKeyboardButton("🚩 Flag", callback_data=f"feedback:flag:{question_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_flag_subcategories(question_id: str) -> InlineKeyboardMarkup:
    """Build flag subcategory selection keyboard."""
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"{data}:{question_id}")]
        for label, data in FLAG_SUBCATEGORIES
    ]
    return InlineKeyboardMarkup(keyboard)
