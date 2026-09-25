import sys
from pathlib import Path

import pandas as pd


# ============================================================
# XAU_AI loyiha papkasi
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from memory.database import get_connection


# ============================================================
# CANDLE HISTORY
# ============================================================

def get_candles(
    timeframe: str,
    limit: int = 1000
) -> pd.DataFrame:

    conn = get_connection()

    query = """
        SELECT
            timeframe,
            open_time,
            open,
            high,
            low,
            close,
            volume,
            tick_volume,
            is_open
        FROM candles
        WHERE timeframe = ?
        ORDER BY open_time DESC
        LIMIT ?
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(
            timeframe,
            limit
        )
    )

    conn.close()


    if df.empty:
        return df


    # ========================================================
    # Numeric columns
    # ========================================================

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "tick_volume"
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )


    # ========================================================
    # Datetime
    # ========================================================

    df["open_time"] = pd.to_datetime(
        df["open_time"],
        errors="coerce"
    )


    # ========================================================
    # Chronological order
    # ========================================================

    df = df.sort_values(
        "open_time"
    ).reset_index(
        drop=True
    )


    return df


# ============================================================
# 5M HISTORY
# ============================================================

def get_5m_candles(
    limit: int = 1000
) -> pd.DataFrame:

    return get_candles(
        timeframe="5m",
        limit=limit
    )


# ============================================================
# 15M HISTORY
# ============================================================

def get_15m_candles(
    limit: int = 1000
) -> pd.DataFrame:

    return get_candles(
        timeframe="15m",
        limit=limit
    )


# ============================================================
# 1H HISTORY
# ============================================================

def get_1h_candles(
    limit: int = 1000
) -> pd.DataFrame:

    return get_candles(
        timeframe="1h",
        limit=limit
    )


# ============================================================
# 4H HISTORY
# ============================================================

def get_4h_candles(
    limit: int = 1000
) -> pd.DataFrame:

    return get_candles(
        timeframe="4h",
        limit=limit
    )


# ============================================================
# 1D HISTORY
# ============================================================

def get_1d_candles(
    limit: int = 1000
) -> pd.DataFrame:

    return get_candles(
        timeframe="1d",
        limit=limit
    )


# ============================================================
# DATABASE SUMMARY
# ============================================================

def print_history_summary():

    print()
    print("=" * 60)
    print("XAU_AI MARKET MEMORY")
    print("=" * 60)


    timeframes = [
        "5m",
        "15m",
        "1h",
        "4h",
        "1d"
    ]


    for timeframe in timeframes:

        df = get_candles(
            timeframe,
            limit=1000
        )


        if df.empty:

            print(
                f"{timeframe.upper():>4}: "
                f"0 candle"
            )

            continue


        first_time = df[
            "open_time"
        ].iloc[0]

        last_time = df[
            "open_time"
        ].iloc[-1]


        print(
            f"{timeframe.upper():>4}: "
            f"{len(df):>5} candle | "
            f"{first_time} -> {last_time}"
        )


    print("=" * 60)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print_history_summary()


    df = get_5m_candles(
        limit=1000
    )


    print()

    print(
        "5M DataFrame:"
    )

    print(
        df.tail(5).to_string(
            index=False
        )
    )
