import sys
from pathlib import Path

import pandas as pd


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORTS
# ============================================================

from memory.history import get_5m_candles
from analysis.scalping_5m import analyze_5m
from analysis.scalping_levels import generate_scalping_levels


# ============================================================
# SETTINGS
# ============================================================

CANDLE_LIMIT = 500

# Number of candles used to build each analysis.
ANALYSIS_WINDOW = 220

# How many future candles are checked after a signal.
MAX_FORWARD_CANDLES = 60


# ============================================================
# RESULT HELPERS
# ============================================================

def empty_result():
    return {
        "total": 0,
        "buy": 0,
        "sell": 0,
        "tp1": 0,
        "tp2": 0,
        "sl": 0,
        "open": 0,
        "total_r": 0.0,
        "results": [],
    }


# ============================================================
# CHECK FUTURE PRICE ACTION
# ============================================================

def evaluate_trade(
    direction,
    entry,
    stop_loss,
    tp1,
    tp2,
    future_df
):
    """
    Evaluate a historical trade using only future candles.

    Conservative rule:

    If SL and TP are touched in the same candle,
    SL is counted first.

    Returns:
        result
        result_r
        bars
    """

    direction = str(direction).upper()

    for bars, (_, candle) in enumerate(
        future_df.iterrows(),
        start=1
    ):

        high = float(candle["high"])
        low = float(candle["low"])

        # ----------------------------------------------------
        # SELL
        # ----------------------------------------------------

        if direction == "SELL":

            sl_hit = high >= stop_loss
            tp1_hit = low <= tp1
            tp2_hit = low <= tp2

            # Conservative:
            # SL first if both are touched.
            if sl_hit:
                return "SL", -1.0, bars

            if tp2_hit:
                return "TP2", 2.5, bars

            if tp1_hit:
                return "TP1", 1.5, bars

        # ----------------------------------------------------
        # BUY
        # ----------------------------------------------------

        elif direction == "BUY":

            sl_hit = low <= stop_loss
            tp1_hit = high >= tp1
            tp2_hit = high >= tp2

            # Conservative:
            # SL first if both are touched.
            if sl_hit:
                return "SL", -1.0, bars

            if tp2_hit:
                return "TP2", 2.5, bars

            if tp1_hit:
                return "TP1", 1.5, bars

    return "OPEN", 0.0, len(future_df)


# ============================================================
# MAIN BACKTEST
# ============================================================

def run_backtest():

    print("=" * 70)
    print("XAU/USD 5M SCALPING BACKTEST V2")
    print("=" * 70)

    # --------------------------------------------------------
    # Load history
    # --------------------------------------------------------

    df = get_5m_candles(
        limit=CANDLE_LIMIT
    )

    if df.empty:

        print("ERROR: No 5M candles found.")

        return

    print(
        f"Loaded 5M candles: {len(df)}"
    )

    print(
        f"Period: {df['open_time'].iloc[0]} -> "
        f"{df['open_time'].iloc[-1]}"
    )

    # --------------------------------------------------------
    # Validate minimum history
    # --------------------------------------------------------

    required = (
        ANALYSIS_WINDOW +
        MAX_FORWARD_CANDLES +
        5
    )

    if len(df) < required:

        print()
        print(
            "WARNING: Not enough historical data."
        )

        print(
            f"Required at least: {required}"
        )

        print(
            f"Available: {len(df)}"
        )

        print()
        print(
            "The collector should continue collecting "
            "5M candles."
        )

        return

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    stats = empty_result()

    # --------------------------------------------------------
    # Backtest loop
    # --------------------------------------------------------

    start_index = ANALYSIS_WINDOW

    end_index = (
        len(df) -
        1
    )

    print()
    print("-" * 70)
    print("RUNNING BACKTEST...")
    print("-" * 70)

    for i in range(
        start_index,
        end_index
    ):

        # ====================================================
        # Historical data available at time i
        # ====================================================

        history_start = max(
            0,
            i - ANALYSIS_WINDOW + 1
        )

        history_df = df.iloc[
            history_start:i + 1
        ].copy()

        # ----------------------------------------------------
        # Analyze historical state
        # ----------------------------------------------------

        try:

            analysis = analyze_5m(
                history_df
            )

        except Exception:

            continue

        if not isinstance(
            analysis,
            dict
        ):
            continue

        # ----------------------------------------------------
        # Generate historical levels
        # ----------------------------------------------------

        try:

            levels = generate_scalping_levels(
                df=history_df,
                analysis_result=analysis
            )

        except Exception:

            continue

        if not isinstance(
            levels,
            dict
        ):
            continue

        if levels.get("status") != "READY":
            continue

        direction = levels.get(
            "direction"
        )

        entry = levels.get(
            "entry"
        )

        stop_loss = levels.get(
            "stop_loss"
        )

        tp1 = levels.get(
            "tp1"
        )

        tp2 = levels.get(
            "tp2"
        )

        if not all(
            value is not None
            for value in (
                direction,
                entry,
                stop_loss,
                tp1,
                tp2
            )
        ):
            continue

        # ----------------------------------------------------
        # Future candles
        # ----------------------------------------------------

        future_start = i + 1

        future_end = min(
            len(df),
            future_start +
            MAX_FORWARD_CANDLES
        )

        future_df = df.iloc[
            future_start:future_end
        ].copy()

        if future_df.empty:
            continue

        # ----------------------------------------------------
        # Evaluate
        # ----------------------------------------------------

        result, result_r, bars = evaluate_trade(
            direction=direction,
            entry=float(entry),
            stop_loss=float(stop_loss),
            tp1=float(tp1),
            tp2=float(tp2),
            future_df=future_df
        )

        # ----------------------------------------------------
        # Save result
        # ----------------------------------------------------

        stats["total"] += 1

        if direction == "BUY":
            stats["buy"] += 1

        elif direction == "SELL":
            stats["sell"] += 1

        if result == "TP1":
            stats["tp1"] += 1

        elif result == "TP2":
            stats["tp2"] += 1

        elif result == "SL":
            stats["sl"] += 1

        elif result == "OPEN":
            stats["open"] += 1

        stats["total_r"] += result_r

        stats["results"].append(
            {
                "time": df["open_time"].iloc[i],
                "direction": direction,
                "entry": float(entry),
                "stop_loss": float(stop_loss),
                "tp1": float(tp1),
                "tp2": float(tp2),
                "result": result,
                "r": result_r,
                "bars": bars,
            }
        )

    # ========================================================
    # PRINT RESULTS
    # ========================================================

    print()
    print("=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)

    total = stats["total"]

    print()
    print(
        f"TOTAL SIGNALS : {total}"
    )

    print(
        f"BUY            : {stats['buy']}"
    )

    print(
        f"SELL           : {stats['sell']}"
    )

    print()
    print(
        f"TP1            : {stats['tp1']}"
    )

    print(
        f"TP2            : {stats['tp2']}"
    )

    print(
        f"SL             : {stats['sl']}"
    )

    print(
        f"OPEN           : {stats['open']}"
    )

    # --------------------------------------------------------
    # Win rate
    # --------------------------------------------------------

    closed = (
        stats["tp1"] +
        stats["tp2"] +
        stats["sl"]
    )

    if closed > 0:

        wins = (
            stats["tp1"] +
            stats["tp2"]
        )

        win_rate = (
            wins /
            closed *
            100
        )

    else:

        win_rate = 0.0

    print()
    print(
        f"CLOSED         : {closed}"
    )

    print(
        f"WIN RATE       : {win_rate:.2f}%"
    )

    # --------------------------------------------------------
    # R statistics
    # --------------------------------------------------------

    print()
    print(
        f"TOTAL R        : {stats['total_r']:.2f}"
    )

    if total > 0:

        avg_r = (
            stats["total_r"] /
            total
        )

    else:

        avg_r = 0.0

    print(
        f"AVERAGE R      : {avg_r:.3f}"
    )

    # --------------------------------------------------------
    # Recent trades
    # --------------------------------------------------------

    print()
    print("-" * 70)
    print("RECENT TRADES")
    print("-" * 70)

    recent = stats["results"][-10:]

    if not recent:

        print("No trades generated.")

    else:

        for trade in recent:

            print(
                f"{trade['time']} | "
                f"{trade['direction']:4} | "
                f"Entry {trade['entry']:.3f} | "
                f"SL {trade['stop_loss']:.3f} | "
                f"TP1 {trade['tp1']:.3f} | "
                f"TP2 {trade['tp2']:.3f} | "
                f"{trade['result']:4} | "
                f"{trade['r']:+.1f}R | "
                f"{trade['bars']} bars"
            )

    print()
    print("=" * 70)
    print("5M BACKTEST FINISHED")
    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_backtest()
