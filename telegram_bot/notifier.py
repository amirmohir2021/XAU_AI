import os
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from telegram import Bot


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def _format_price(value):
    if value is None:
        return "N/A"

    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def format_trade_notification(result):
    """
    XAU_AI StrategyResult yoki dict natijasini
    Telegram xabariga aylantiradi.
    """

    if hasattr(result, "to_dict"):
        data = result.to_dict()
    elif isinstance(result, dict):
        data = result
    else:
        return str(result)

    signal = data.get("signal", "NO_TRADE")

    if signal not in ("BUY", "SELL"):
        return None

    direction_emoji = "🟢" if signal == "BUY" else "🔴"

    entry = data.get("entry")
    stop_loss = data.get("stop_loss")
    tp1 = data.get("tp1")
    tp2 = data.get("tp2")

    trend_1d = data.get("trend_1d", "N/A")
    trend_4h = data.get("trend_4h", "N/A")
    trend_1h = data.get("trend_1h", "N/A")
    trend_15m = data.get("trend_15m", "N/A")
    trend_5m = data.get("trend_5m", "N/A")

    confirmations = data.get("confirmation_count", 0)
    htf_agreement = data.get("htf_agreement", "N/A")

    strategy_name = data.get("strategy_name", "N/A")
    strategy_version = data.get("strategy_version", "N/A")

    setup = data.get("setup", "N/A")
    status = data.get("status", "N/A")

    risk = data.get("risk")

    metadata = data.get("metadata") or {}

    v31_confidence = metadata.get("v31_confidence")
    market_phase = metadata.get("market_phase")
    entry_trigger = metadata.get("entry_trigger")

    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"{direction_emoji} XAU/USD {signal}",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        f"💰 ENTRY: {_format_price(entry)}",
        f"🛑 SL: {_format_price(stop_loss)}",
        f"🎯 TP1: {_format_price(tp1)}",
        f"🎯 TP2: {_format_price(tp2)}",
        f"⚖️ RISK: {_format_price(risk)}",
        "",
        "📊 MULTI-TIMEFRAME",
        f"1D  : {trend_1d}",
        f"4H  : {trend_4h}",
        f"1H  : {trend_1h}",
        f"15M : {trend_15m}",
        f"5M  : {trend_5m}",
        "",
        f"✅ CONFIRMATIONS: {confirmations}",
        f"🔗 HTF AGREEMENT: {htf_agreement}",
        "",
        "🧠 STRATEGY",
        f"Name    : {strategy_name}",
        f"Version : {strategy_version}",
        f"Setup   : {setup}",
        f"Status  : {status}",
    ]

    if v31_confidence is not None:
        lines.append(f"Alignment: {v31_confidence}")

    if market_phase:
        lines.append(f"Phase: {market_phase}")

    if entry_trigger:
        lines.append(f"Trigger: {entry_trigger}")

    lines.extend(
        [
            "",
            "⚠️ XAU_AI analysis signal.",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
    )

    return "\n".join(lines)


async def _send_message_async(message):
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN .env faylida topilmadi."
        )

    if not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID .env faylida topilmadi."
        )

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    finally:
        await bot.shutdown()


def send_trade_notification(result):
    """
    BUY/SELL bo'lsa Telegramga yuboradi.
    NO_TRADE bo'lsa hech narsa yubormaydi.

    True  -> yuborildi
    False -> yuborilmadi
    """

    message = format_trade_notification(result)

    if not message:
        return False

    asyncio.run(_send_message_async(message))

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("XAU_AI TELEGRAM NOTIFIER")
    print("=" * 60)

    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN topilmadi.")
    else:
        print("TELEGRAM_BOT_TOKEN: OK")

    if not TELEGRAM_CHAT_ID:
        print("TELEGRAM_CHAT_ID: MISSING")
    else:
        print("TELEGRAM_CHAT_ID: OK")

    print("=" * 60)