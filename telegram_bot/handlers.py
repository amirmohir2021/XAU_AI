import asyncio


from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.keyboards import main_menu_keyboard

from memory.signal_collector import collect_signal
from memory.signal_stats import get_all_signal_stats


# ============================================================
# START
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = (
        "🤖 XAU_AI TELEGRAM BOT\n\n"
        "XAU/USD avtomatik tahlil tizimiga xush kelibsiz.\n\n"
        "Bu bot XAU_AI signal engine'ining natijalarini "
        "Telegram orqali ko'rsatadi.\n\n"
        "Kerakli bo'limni tanlang:"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(),
    )


# ============================================================
# SIGNAL
# ============================================================

async def signal_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = await update.message.reply_text(
        "⏳ XAU/USD tahlil qilinmoqda...\n\n"
        "5M + 15M + 1H + 4H + 1D tekshirilmoqda."
    )

    try:
        result = await asyncio.to_thread(
            collect_signal
        )

        text = format_signal_result(result)

        await message.edit_text(
            text,
            reply_markup=main_menu_keyboard(),
        )

    except Exception as e:
        await message.edit_text(
            "❌ SIGNAL XATOLIGI\n\n"
            f"{type(e).__name__}: {e}",
            reply_markup=main_menu_keyboard(),
        )


# ============================================================
# STATISTICS
# ============================================================

async def stats_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        stats = get_all_signal_stats()

        text = format_stats(stats)

        await update.message.reply_text(
            text,
            reply_markup=main_menu_keyboard(),
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ STATISTICS XATOLIGI\n\n"
            f"{type(e).__name__}: {e}",
            reply_markup=main_menu_keyboard(),
        )


# ============================================================
# STATUS
# ============================================================

async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = (
        "🟢 XAU_AI STATUS\n\n"
        "Market Data       : 🟢\n"
        "HTF Analysis      : 🟢\n"
        "V3.1 Engine       : 🟢\n"
        "5M Engine         : 🟢\n"
        "Liquidity Strategy: 🟢\n"
        "Memory Database   : 🟢\n"
        "Telegram Bot      : 🟢\n\n"
        "SYSTEM: READY"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(),
    )


# ============================================================
# BUTTON CALLBACK
# ============================================================

async def button_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    # --------------------------------------------------------
    # SIGNAL
    # --------------------------------------------------------

    if query.data == "signal":

        await query.edit_message_text(
            "⏳ XAU/USD tahlil qilinmoqda...\n\n"
            "5M + HTF analysis ishlamoqda."
        )

        try:
            result = await asyncio.to_thread(
                collect_signal
            )

            await query.edit_message_text(
                format_signal_result(result),
                reply_markup=main_menu_keyboard(),
            )

        except Exception as e:

            await query.edit_message_text(
                "❌ SIGNAL XATOLIGI\n\n"
                f"{type(e).__name__}: {e}",
                reply_markup=main_menu_keyboard(),
            )

    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    elif query.data == "stats":

        try:
            stats = get_all_signal_stats()

            await query.edit_message_text(
                format_stats(stats),
                reply_markup=main_menu_keyboard(),
            )

        except Exception as e:

            await query.edit_message_text(
                "❌ STATISTICS XATOLIGI\n\n"
                f"{type(e).__name__}: {e}",
                reply_markup=main_menu_keyboard(),
            )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    elif query.data == "status":

        await query.edit_message_text(
            "🟢 XAU_AI STATUS\n\n"
            "Market Data       : 🟢 OK\n"
            "HTF Analysis      : 🟢 OK\n"
            "V3.1 Engine       : 🟢 OK\n"
            "5M Engine         : 🟢 OK\n"
            "Liquidity Strategy: 🟢 OK\n"
            "Memory Database   : 🟢 OK\n"
            "Telegram Bot      : 🟢 OK\n\n"
            "SYSTEM: READY",
            reply_markup=main_menu_keyboard(),
        )


# ============================================================
# FORMAT SIGNAL
# ============================================================

def format_signal_result(result):

    if result is None:
        return "❌ Signal natijasi olinmadi."

    # StrategyResult obyektidan dictionary olish
    if hasattr(result, "to_dict"):
        data = result.to_dict()

    elif isinstance(result, dict):
        data = result

    else:
        return str(result)

    signal = data.get(
        "signal",
        "NO_TRADE"
    )

    price = data.get(
        "price",
        "-"
    )

    confirmations = data.get(
        "confirmation_count",
        data.get("confirmations", 0)
    )

    trend_1d = data.get(
        "trend_1d",
        "-"
    )

    trend_4h = data.get(
        "trend_4h",
        "-"
    )

    trend_1h = data.get(
        "trend_1h",
        "-"
    )

    trend_15m = data.get(
        "trend_15m",
        "-"
    )

    trend_5m = data.get(
        "trend_5m",
        "-"
    )

    htf_agreement = data.get(
        "htf_agreement",
        "-"
    )

    setup = data.get(
        "setup",
        "-"
    )

    entry = data.get(
        "entry"
    )

    stop_loss = data.get(
        "stop_loss"
    )

    tp1 = data.get(
        "tp1"
    )

    tp2 = data.get(
        "tp2"
    )

    risk = data.get(
        "risk"
    )

    rr_tp1 = data.get(
        "rr_tp1"
    )

    rr_tp2 = data.get(
        "rr_tp2"
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    if signal == "BUY":
        icon = "🟢"
    elif signal == "SELL":
        icon = "🔴"
    else:
        icon = "🟡"

    text = (
        f"{icon} XAU/USD SIGNAL\n"
        f"{'=' * 25}\n\n"
        f"SIGNAL       : {signal}\n"
        f"PRICE        : {price}\n"
        f"SETUP        : {setup}\n"
        f"CONFIRMATIONS: {confirmations}\n\n"
        f"1D  : {trend_1d}\n"
        f"4H  : {trend_4h}\n"
        f"1H  : {trend_1h}\n"
        f"15M : {trend_15m}\n"
        f"5M  : {trend_5m}\n"
        f"HTF : {htf_agreement}\n"
    )

    # --------------------------------------------------------
    # Trade levels
    # --------------------------------------------------------

    if signal in ("BUY", "SELL"):

        text += (
            "\n🎯 TRADE LEVELS\n"
            f"{'=' * 25}\n\n"
            f"ENTRY : {entry}\n"
            f"SL    : {stop_loss}\n"
            f"TP1   : {tp1}\n"
            f"TP2   : {tp2}\n"
            f"RISK  : {risk}\n"
            f"RR TP1: {rr_tp1}\n"
            f"RR TP2: {rr_tp2}\n"
        )

    else:

        text += (
            "\n⏸️ TRADE YO'Q\n\n"
            "XAU_AI hozircha tasdiqlangan "
            "BUY/SELL setup topmadi."
        )

    return text


# ============================================================
# FORMAT STATISTICS
# ============================================================

def format_stats(stats):

    if not stats:
        return (
            "📈 XAU_AI STATISTICS\n\n"
            "Hozircha statistika mavjud emas."
        )

    if not isinstance(stats, dict):
        return str(stats)

    total = stats.get(
        "total",
        0
    )

    wins = stats.get(
        "wins",
        0
    )

    losses = stats.get(
        "losses",
        0
    )

    open_count = stats.get(
        "open",
        0
    )

    closed = stats.get(
        "closed",
        0
    )

    win_rate = stats.get(
        "win_rate",
        0
    )

    total_r = stats.get(
        "total_r",
        0
    )

    return (
        "📈 XAU_AI STATISTICS\n"
        "========================\n\n"
        f"TOTAL SIGNALS : {total}\n"
        f"OPEN          : {open_count}\n"
        f"CLOSED        : {closed}\n"
        f"WINS          : {wins}\n"
        f"LOSSES        : {losses}\n"
        f"WIN RATE      : {win_rate}%\n"
        f"TOTAL R       : {total_r}\n"
    )