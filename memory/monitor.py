import time
from datetime import datetime, timezone

from data.market_data import get_xauusd_candles
from memory.signal_collector import collect_signal
from memory.outcome_tracker import update_all_open_signals
from memory.signal_stats import get_all_signal_stats
from telegram_bot.notifier import send_trade_notification


TIMEFRAME = "5m"
CANDLE_LIMIT = 10
CHECK_INTERVAL_SECONDS = 30


def get_latest_closed_candle():
    df = get_xauusd_candles(
        interval=TIMEFRAME,
        limit=CANDLE_LIMIT,
    )

    if df is None or df.empty:
        return None

    if "isOpen" in df.columns:
        df = df[df["isOpen"] == False].copy()

    if df.empty:
        return None

    df = df.sort_values("openTime").reset_index(drop=True)

    return df.iloc[-1]


def print_signal_summary(result):
    if hasattr(result, "to_dict"):
        data = result.to_dict()
    elif isinstance(result, dict):
        data = result
    else:
        print(result)
        return

    signal = data.get("signal", "NO_TRADE")

    print()
    print("-" * 60)
    print("CURRENT XAU_AI SIGNAL")
    print("-" * 60)

    print(f"SIGNAL        : {signal}")
    print(f"SETUP         : {data.get('setup', 'N/A')}")
    print(f"STATUS        : {data.get('status', 'N/A')}")
    print(f"PRICE         : {data.get('price', 'N/A')}")

    print(f"1D            : {data.get('trend_1d', 'N/A')}")
    print(f"4H            : {data.get('trend_4h', 'N/A')}")
    print(f"1H            : {data.get('trend_1h', 'N/A')}")
    print(f"15M           : {data.get('trend_15m', 'N/A')}")
    print(f"5M            : {data.get('trend_5m', 'N/A')}")

    print(f"CONFIRMATIONS : {data.get('confirmation_count', 0)}")
    print(f"HTF AGREEMENT : {data.get('htf_agreement', 'N/A')}")

    if signal in ("BUY", "SELL"):
        print(f"ENTRY         : {data.get('entry')}")
        print(f"STOP LOSS     : {data.get('stop_loss')}")
        print(f"TP1           : {data.get('tp1')}")
        print(f"TP2           : {data.get('tp2')}")
        print(f"RISK          : {data.get('risk')}")

    print("-" * 60)


def print_memory_stats():
    try:
        stats = get_all_signal_stats()

        print()
        print("SIGNAL MEMORY")

        if isinstance(stats, dict):
            print(f"TOTAL  : {stats.get('total', 0)}")
            print(f"WINS   : {stats.get('wins', 0)}")
            print(f"LOSSES : {stats.get('losses', 0)}")
            print(f"OPEN   : {stats.get('open', 0)}")
            print(f"CLOSED : {stats.get('closed', 0)}")
            print(f"WINRATE: {stats.get('win_rate', 0)}%")
            print(f"TOTAL R: {stats.get('total_r', 0)}")
        else:
            print(stats)

    except Exception as exc:
        print(f"Statistics error: {exc}")


def process_new_candle(candle_time):
    print()
    print("=" * 60)
    print("NEW CLOSED 5M CANDLE")
    print("=" * 60)

    print(f"Closed candle time : {candle_time}")

    try:
        candle = get_latest_closed_candle()

        if candle is not None:
            print(f"Closed price       : {candle['close']}")

        print()
        print("Running XAU_AI signal analysis...")

        result = collect_signal()

        print_signal_summary(result)

        signal = None

        if hasattr(result, "signal"):
            signal = result.signal

        elif isinstance(result, dict):
            signal = result.get("signal")

        if signal in ("BUY", "SELL"):
            print()
            print("🚨 TRADE SIGNAL DETECTED")
            print(f"Direction: {signal}")
            print("Sending Telegram notification...")

            try:
                sent = send_trade_notification(result)

                if sent:
                    print("TELEGRAM NOTIFICATION: SENT")
                else:
                    print("TELEGRAM NOTIFICATION: SKIPPED")

            except Exception as exc:
                print(f"TELEGRAM NOTIFICATION ERROR: {exc}")

        else:
            print()
            print("No BUY/SELL signal.")
            print("Telegram notification: NOT SENT")

        try:
            updated = update_all_open_signals()

            if updated is not None:
                print(f"OPEN SIGNALS UPDATED: {updated}")

        except Exception as exc:
            print(f"Outcome tracker error: {exc}")

        print_memory_stats()

    except Exception as exc:
        print()
        print(f"SIGNAL PROCESSING ERROR: {exc}")


def main():
    print("=" * 60)
    print("XAU_AI REAL-TIME MONITOR")
    print("=" * 60)

    print(f"TIMEFRAME         : {TIMEFRAME}")
    print(f"CHECK INTERVAL    : {CHECK_INTERVAL_SECONDS} seconds")
    print(
        f"STARTED           : "
        f"{datetime.now(timezone.utc).isoformat()}"
    )

    print("=" * 60)

    last_candle_time = None

    while True:
        try:
            candle = get_latest_closed_candle()

            if candle is None:
                print("No closed candle available.")
                time.sleep(CHECK_INTERVAL_SECONDS)
                continue

            candle_time = candle["openTime"]

            if last_candle_time is None:
                last_candle_time = candle_time

                print()
                print("Initial closed candle detected:")
                print(candle_time)

                process_new_candle(candle_time)

            elif candle_time != last_candle_time:
                last_candle_time = candle_time

                process_new_candle(candle_time)

            else:
                now = datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                print(
                    f"[{now} UTC] "
                    f"No new closed 5M candle. "
                    f"Latest: {candle_time}"
                )

            time.sleep(CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print()
            print("=" * 60)
            print("XAU_AI MONITOR STOPPED")
            print("=" * 60)
            break

        except Exception as exc:
            print()
            print(f"MONITOR ERROR: {exc}")
            print(
                f"Retrying in "
                f"{CHECK_INTERVAL_SECONDS} seconds..."
            )

            time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()