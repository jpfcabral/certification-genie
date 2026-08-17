from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.api.domain.enums.domain_type import DomainType


def build_domain_selector() -> InlineKeyboardMarkup:
    """Build domain selection keyboard from available AI-103 domains."""
    keyboard = [
        [InlineKeyboardButton(domain.value, callback_data=f"domain:{domain.name}")]
        for domain in DomainType
    ]
    return InlineKeyboardMarkup(keyboard)
