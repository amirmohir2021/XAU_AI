from __future__ import annotations

import time
from datetime import datetime, timezone

from data.market_data import get_xauusd_candles
from memory.signal_collector import collect_signal
from memory.outcome_tracker import update_all_open_signals
from memory.signal_stats import get_all_signal_stats


TIMEFRAME = "5m"
CANDLE_LIMIT = 10

# Bozor yangi 5M candle yopilishini tekshirish oralig‘i.
CHECK_INTERVAL_SECONDS = 30


def get_latest_closed_candle_time():
    """
    Return the latest CLOSED 5M candle time.

    The currently forming candle is ignored.
    """

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

    return df.iloc[-1]["openTime"]


def print_monitor_header():
    print()
    print("=" * 100)
    print("XAU_AI REAL-TIME MONITOR")
    print("=" * 100)

    print(f"TIMEFRAME           : {TIMEFRAME}")
    print(
        f"CHECK INTERVAL      : "
        f"{CHECK_INTERVAL_SECONDS} seconds"
    )

    print(
        f"STARTED             : "
        f"{datetime.now(timezone.utc).isoformat()}"
    )

    print("=" * 100)


def print_cycle_info(candle_time):
    print()
    print("-" * 100)

    print(
        f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] "
        f"NEW CLOSED 5M CANDLE"
    )

    print(
        f"Closed candle time  : {candle_time}"
    )

    print("-" * 100)


def print_statistics():
    """
    Print current signal statistics.
    """

    stats = get_all_signal_stats()

    overall = stats["overall"]
    buy = stats["buy"]
    sell = stats["sell"]

    print()
    print("-" * 100)
    print("CURRENT SIGNAL MEMORY")
    print("-" * 100)

    print(
        f"TOTAL   : {overall['total']}"
    )

    print(
        f"OPEN    : {overall['open']}"
    )

    print(
        f"WINS    : {overall['wins']}"
    )

    print(
        f"LOSSES  : {overall['losses']}"
    )

    print(
        f"WIN RATE: {overall['win_rate']:.2f}%"
    )

    print(
        f"TOTAL R : {overall['total_r']:.2f}"
    )

    print(
        f"BUY     : {buy['total']}"
    )

    print(
        f"SELL    : {sell['total']}"
    )


def process_new_candle(candle_time):
    """
    Run one complete analysis cycle.

    1. Analyze market
    2. Save BUY/SELL if generated
    3. Update previous open signals
    4. Print current statistics
    """

    print_cycle_info(candle_time)

    # ---------------------------------------------------------
    # 1. SIGNAL COLLECTION
    # ---------------------------------------------------------

    print()
    print("Running XAU_AI signal analysis...")

    result = collect_signal()

    # ---------------------------------------------------------
    # 2. OUTCOME TRACKING
    # ---------------------------------------------------------

    print()
    print("-" * 100)
    print("OUTCOME TRACKER")
    print("-" * 100)

    updated = update_all_open_signals()

    print(
        f"OPEN SIGNALS UPDATED: {updated}"
    )

    # ---------------------------------------------------------
    # 3. CURRENT STATISTICS
    # ---------------------------------------------------------

    print_statistics()

    return result


def run_monitor():
    """
    Continuous XAU_AI monitoring loop.

    The system processes only a NEW closed 5M candle.

    This prevents repeated analysis of the same candle.
    """

    print_monitor_header()

    last_processed_candle = None

    print()
    print("Waiting for a new closed 5M candle...")

    while True:

        try:
            latest_closed = get_latest_closed_candle_time()

            if latest_closed is None:
                print(
                    "[WAIT] "
                    "No closed 5M candle available."
                )

            else:

                if last_processed_candle is None:
                    # On startup, process the latest closed candle once.
                    last_processed_candle = latest_closed

                    process_new_candle(
                        latest_closed
                    )

                elif latest_closed != last_processed_candle:

                    last_processed_candle = latest_closed

                    process_new_candle(
                        latest_closed
                    )

                else:
                    print(
                        f"[WAIT] "
                        f"No new 5M candle. "
                        f"Last: {latest_closed}"
                    )

        except KeyboardInterrupt:

            print()
            print("=" * 100)
            print("XAU_AI MONITOR STOPPED")
            print("=" * 100)

            break

        except Exception as exc:

            print()
            print("-" * 100)
            print("MONITOR ERROR")
            print("-" * 100)

            print(
                f"{type(exc).__name__}: {exc}"
            )

            print(
                "Monitor will continue..."
            )

        time.sleep(
            CHECK_INTERVAL_SECONDS
        )


if __name__ == "__main__":
    run_monitor()