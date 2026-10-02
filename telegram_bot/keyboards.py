from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 SIGNAL", callback_data="signal"),
            InlineKeyboardButton("📈 STATISTICS", callback_data="stats"),
        ],
        [
            InlineKeyboardButton("🟢 STATUS", callback_data="status"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)