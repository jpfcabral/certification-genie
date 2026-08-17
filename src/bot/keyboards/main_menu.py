from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_main_menu() -> InlineKeyboardMarkup:
    """Build the main menu keyboard with Training, Simulation, and Free Q&A buttons."""
    keyboard = [
        [InlineKeyboardButton("📚 Training", callback_data="menu:training")],
        [InlineKeyboardButton("📝 Simulation", callback_data="menu:simulation")],
        [InlineKeyboardButton("💬 Free Q&A", callback_data="menu:free_qa")],
    ]
    return InlineKeyboardMarkup(keyboard)
