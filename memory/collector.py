import sys
import time
from pathlib import Path

import pandas as pd


# ============================================================
# PROJECT ROOT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# ============================================================
# IMPORTS
# ============================================================

from data.market_data import get_xauusd_candles

from memory.database import (
    initialize_database,
    save_candle,
    get_candle_count,
)


# ============================================================
# SETTINGS
# ============================================================

COLLECT_INTERVAL = 60

FETCH_LIMITS = {
    "5m": 20,
    "15m": 10,
    "1h": 5,
    "4h": 3,
    "1d": 2,
}


# ============================================================
# SAVE DATAFRAME
# ============================================================

def save_dataframe_candles(
    timeframe: str,
    df: pd.DataFrame
):
    saved = 0

    if df is None or df.empty:
        print("  No data received.")
        return 0

    for _, row in df.iterrows():

        try:
            # ------------------------------------------------
            # BiQuote column names
            # ------------------------------------------------

            open_time = row["openTime"]

            open_price = float(row["open"])
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])

            volume = float(
                row.get("volume", 0) or 0
            )

            tick_volume = float(
                row.get("tickVolume", 0) or 0
            )

            is_open = bool(
                row.get("isOpen", False)
            )

            # ------------------------------------------------
            # Timestamp
            # ------------------------------------------------

            open_time = pd.to_datetime(
                open_time,
                utc=True
            )

            open_time = open_time.isoformat()

            # ------------------------------------------------
            # Save to SQLite
            # ------------------------------------------------

            save_candle(
                timeframe=timeframe,
                open_time=open_time,
                open_price=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                tick_volume=tick_volume,
                is_open=is_open,
            )

            saved += 1

        except Exception as e:

            print(
                f"  Candle save error: {e}"
            )

    return saved


# ============================================================
# COLLECT ONE TIMEFRAME
# ============================================================

def collect_timeframe(
    timeframe: str,
    limit: int
):

    print()
    print(f"[{timeframe.upper()}]")
    print(
        f"API request: last {limit} candles"
    )

    try:

        df = get_xauusd_candles(
            interval=timeframe,
            limit=limit
        )

    except Exception as e:

        print(
            f"API error: {e}"
        )

        return 0

    if df is None or df.empty:

        print("API candles: 0")
        print("Saved/updated: 0")

        return 0

    print(
        f"API candles: {len(df)}"
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    saved = save_dataframe_candles(
        timeframe=timeframe,
        df=df
    )

    total = get_candle_count(
        timeframe
    )

    print(
        f"Saved/updated: {saved}"
    )

    print(
        f"DB total:      {total}"
    )

    return saved


# ============================================================
# COLLECT ALL
# ============================================================

def collect_all():

    print()
    print("=" * 70)
    print("XAU_AI MARKET COLLECTOR V3")
    print("=" * 70)

    initialize_database()

    total_saved = 0

    for timeframe, limit in FETCH_LIMITS.items():

        saved = collect_timeframe(
            timeframe,
            limit
        )

        total_saved += saved

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    print()
    print("-" * 70)
    print("Cycle finished.")
    print(
        f"Rows processed: {total_saved}"
    )

    print()
    print("DATABASE STATUS")

    print(
        f"5M : {get_candle_count('5m')}"
    )

    print(
        f"15M: {get_candle_count('15m')}"
    )

    print(
        f"1H : {get_candle_count('1h')}"
    )

    print(
        f"4H : {get_candle_count('4h')}"
    )

    print(
        f"1D : {get_candle_count('1d')}"
    )

    print("=" * 70)


# ============================================================
# CONTINUOUS MODE
# ============================================================

def run_forever():

    initialize_database()

    while True:

        try:

            collect_all()

        except KeyboardInterrupt:

            print()
            print(
                "Collector stopped by user."
            )

            break

        except Exception as e:

            print()
            print(
                f"Collector error: {e}"
            )

        print()
        print(
            f"Waiting {COLLECT_INTERVAL} seconds..."
        )

        try:

            time.sleep(
                COLLECT_INTERVAL
            )

        except KeyboardInterrupt:

            print()
            print(
                "Collector stopped by user."
            )

            break


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_forever()