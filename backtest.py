import pandas as pd
import numpy as np

from data.market_data import get_xauusd_candles
from analysis.structure import analyze_structure
from analysis.signal_engine import generate_signal


# ============================================================
# XAU_AI BACKTEST V1
# ============================================================

TIMEFRAME = "15m"
LIMIT = 1000

# Har bir signal uchun keyingi nechta candle tekshiriladi
MAX_FORWARD_CANDLES = 96


def prepare_data():
    print("=" * 70)
    print("XAU_AI BACKTEST V1")
    print("=" * 70)

    print(f"\nLoading {TIMEFRAME} historical data...")

    df = get_xauusd_candles(
        interval=TIMEFRAME,
        limit=LIMIT
    )

    if df is None or df.empty:
        raise RuntimeError("Market data yuklanmadi.")

    df = df.reset_index(drop=True)

    print(f"Loaded candles: {len(df)}")

    return df


def calculate_atr(df, period=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    return true_range.rolling(period).mean()


def build_timeframe_data(df, current_index):
    """
    Signal engine uchun kerakli timeframe ma'lumotlarini
    tayyorlash.

    Hozirgi bosqichda mavjud tarixiy datasetdan
    signalga kerakli snapshot olinadi.
    """

    available = df.iloc[:current_index + 1].copy()

    if len(available) < 100:
        return None

    atr = calculate_atr(available)

    latest = available.iloc[-1]

    indicators = {
        "PRICE": float(latest["close"]),
        "ATR14": float(atr.iloc[-1])
        if not pd.isna(atr.iloc[-1]) else 0.0,
    }

    return {
        "data": available,
        "indicators": indicators
    }


def check_trade_result(
    df,
    signal_index,
    signal
):
    """
    BUY / SELL signal chiqqandan keyingi shamlarni tekshiradi.

    Natija:
        TP1
        TP2
        SL
        OPEN
    """

    direction = signal.get("signal")

    trade = signal.get("trade_levels") or {}

    entry = trade.get("entry")
    stop_loss = trade.get("stop_loss")
    tp1 = trade.get("tp1")
    tp2 = trade.get("tp2")

    if None in (entry, stop_loss, tp1, tp2):
        return {
            "result": "INVALID",
            "bars": 0,
            "r": 0.0
        }

    future = df.iloc[
        signal_index + 1:
        signal_index + 1 + MAX_FORWARD_CANDLES
    ]

    if future.empty:
        return {
            "result": "OPEN",
            "bars": 0,
            "r": 0.0
        }

    risk = abs(entry - stop_loss)

    for bar_count, (_, candle) in enumerate(
        future.iterrows(),
        start=1
    ):

        high = float(candle["high"])
        low = float(candle["low"])

        # ====================================================
        # SELL
        # ====================================================

        if direction == "SELL":

            sl_hit = high >= stop_loss
            tp1_hit = low <= tp1
            tp2_hit = low <= tp2

            # Bir candle ichida SL va TP birga tegsa,
            # konservativ ravishda SL deb hisoblaymiz.
            if sl_hit:
                return {
                    "result": "SL",
                    "bars": bar_count,
                    "r": -1.0
                }

            if tp2_hit:
                return {
                    "result": "TP2",
                    "bars": bar_count,
                    "r": abs(entry - tp2) / risk
                }

            if tp1_hit:
                return {
                    "result": "TP1",
                    "bars": bar_count,
                    "r": abs(entry - tp1) / risk
                }

        # ====================================================
        # BUY
        # ====================================================

        elif direction == "BUY":

            sl_hit = low <= stop_loss
            tp1_hit = high >= tp1
            tp2_hit = high >= tp2

            if sl_hit:
                return {
                    "result": "SL",
                    "bars": bar_count,
                    "r": -1.0
                }

            if tp2_hit:
                return {
                    "result": "TP2",
                    "bars": bar_count,
                    "r": abs(tp2 - entry) / risk
                }

            if tp1_hit:
                return {
                    "result": "TP1",
                    "bars": bar_count,
                    "r": abs(tp1 - entry) / risk
                }

    return {
        "result": "OPEN",
        "bars": len(future),
        "r": 0.0
    }


def run_backtest():

    df = prepare_data()

    print("\nCalculating ATR...")

    df["ATR14"] = calculate_atr(df)

    results = []

    # Signalni juda boshidan emas,
    # indikatorlar yetarli bo'lgan joydan boshlaymiz.
    start_index = 200

    print("\nRunning historical simulation...")
    print("-" * 70)

    for i in range(
        start_index,
        len(df) - MAX_FORWARD_CANDLES
    ):

        # --------------------------------------------
        # Hozirgi tarix
        # --------------------------------------------

        current = df.iloc[:i + 1].copy()

        # Yetarli data bo'lmasa o'tkazib yuboramiz
        if len(current) < 100:
            continue

        try:

            # ----------------------------------------
            # Structure
            # ----------------------------------------

            structure = analyze_structure(current)

            # ----------------------------------------
            # Hozirgi versiyada signal engine
            # bir nechta timeframe kutadi.
            #
            # Backtest V1 da mavjud timeframe snapshot
            # ishlatiladi.
            # ----------------------------------------

            atr = float(current["ATR14"].iloc[-1])

            if atr <= 0 or np.isnan(atr):
                continue

            price = float(current["close"].iloc[-1])

            # Minimal indicator snapshot
            indicators = {
                "PRICE": price,
                "ATR14": atr,
            }

            # Bu bosqichda signal engine'ning to'liq
            # timeframe pipeline'ini alohida adapter
            # orqali ulaymiz.
            #
            # Hozircha faqat structure statistikasi
            # yig'iladi.

            if structure:

                trend = structure.get(
                    "trend",
                    "NEUTRAL"
                )

                bos = structure.get(
                    "bos",
                    []
                )

                choch = structure.get(
                    "choch",
                    []
                )

                results.append({
                    "index": i,
                    "price": price,
                    "trend": trend,
                    "bos": len(bos),
                    "choch": len(choch)
                })

        except Exception as e:

            print(
                f"Warning at index {i}: {e}"
            )

    return df, results


def print_statistics(df, results):

    print("\n")
    print("=" * 70)
    print("BACKTEST V1 RESULTS")
    print("=" * 70)

    print(f"Historical candles : {len(df)}")
    print(f"Structure samples  : {len(results)}")

    if not results:
        print("\nNo results.")
        return

    result_df = pd.DataFrame(results)

    print("\nMARKET STRUCTURE")

    print(
        result_df["trend"]
        .value_counts()
        .to_string()
    )

    print("\nAverage BOS:")
    print(
        round(
            result_df["bos"].mean(),
            2
        )
    )

    print("\nAverage CHOCH:")
    print(
        round(
            result_df["choch"].mean(),
            2
        )
    )

    print("\nLatest samples:")
    print(
        result_df.tail(10).to_string(
            index=False
        )
    )

    print("\n" + "=" * 70)
    print("BACKTEST FINISHED")
    print("=" * 70)


if __name__ == "__main__":

    df, results = run_backtest()

    print_statistics(
        df,
        results
    )