import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


# ============================================================
# PROJECT ROOT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# ============================================================
# TOKEN CHECK
# ============================================================

if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN .env faylida topilmadi."
    )


# ============================================================
# XAU_AI HANDLERS
# ============================================================

from telegram_bot.handlers import (
    start_command,
    signal_command,
    stats_command,
    status_command,
    button_callback,
)


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    print(
        f"Telegram error: {context.error}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("XAU_AI TELEGRAM BOT")
    print("=" * 60)

    application = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "signal",
            signal_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "stats",
            stats_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "status",
            status_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            button_callback,
        )
    )

    application.add_error_handler(
        error_handler,
    )

    print()
    print("Bot starting...")
    print()
    print("Commands:")
    print("  /start")
    print("  /signal")
    print("  /stats")
    print("  /status")
    print()
    print("Press CTRL+C to stop.")
    print("=" * 60)

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()