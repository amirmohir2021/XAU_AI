import sys
from pathlib import Path
from collections import defaultdict

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
ANALYSIS_WINDOW = 220
MAX_FORWARD_CANDLES = 60


# ============================================================
# SESSION
# ============================================================

def get_session(timestamp):
    """
    Simple UTC session classification.

    These are analytical buckets, not broker-specific
    official session boundaries.
    """

    hour = timestamp.hour

    if 0 <= hour < 8:
        return "ASIA"

    if 8 <= hour < 13:
        return "LONDON"

    if 13 <= hour < 21:
        return "NEW_YORK"

    return "OFF_SESSION"


# ============================================================
# TRADE EVALUATION
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
    Conservative historical evaluation.

    If SL and TP are touched in the same candle,
    SL is counted first.
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

            if sl_hit:
                return "SL", -1.0, bars

            if tp2_hit:
                return "TP2", 2.5, bars

            if tp1_hit:
                return "TP1", 1.5, bars

    return "OPEN", 0.0, len(future_df)


# ============================================================
# SAFE PERCENTAGE
# ============================================================

def percentage(value, total):

    if total <= 0:
        return 0.0

    return value / total * 100.0


# ============================================================
# STATISTICS
# ============================================================

def calculate_group_stats(trades):

    total = len(trades)

    if total == 0:

        return {
            "signals": 0,
            "wins": 0,
            "losses": 0,
            "open": 0,
            "win_rate": 0.0,
            "total_r": 0.0,
            "avg_r": 0.0,
            "profit_factor": 0.0,
        }

    wins = sum(
        1
        for trade in trades
        if trade["result"] in ("TP1", "TP2")
    )

    losses = sum(
        1
        for trade in trades
        if trade["result"] == "SL"
    )

    open_trades = sum(
        1
        for trade in trades
        if trade["result"] == "OPEN"
    )

    total_r = sum(
        trade["r"]
        for trade in trades
    )

    avg_r = total_r / total

    gross_profit = sum(
        trade["r"]
        for trade in trades
        if trade["r"] > 0
    )

    gross_loss = abs(
        sum(
            trade["r"]
            for trade in trades
            if trade["r"] < 0
        )
    )

    if gross_loss > 0:
        profit_factor = (
            gross_profit /
            gross_loss
        )
    else:
        profit_factor = 0.0

    closed = wins + losses

    return {
        "signals": total,
        "wins": wins,
        "losses": losses,
        "open": open_trades,
        "win_rate": percentage(
            wins,
            closed
        ),
        "total_r": total_r,
        "avg_r": avg_r,
        "profit_factor": profit_factor,
    }


# ============================================================
# MAX DRAWDOWN
# ============================================================

def calculate_max_drawdown(trades):

    if not trades:
        return 0.0

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for trade in trades:

        equity += trade["r"]

        if equity > peak:
            peak = equity

        drawdown = peak - equity

        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return max_drawdown


# ============================================================
# MAIN BACKTEST
# ============================================================

def run_backtest():

    print("=" * 70)
    print("XAU/USD 5M SCALPING BACKTEST V3")
    print("=" * 70)

    # --------------------------------------------------------
    # Load data
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

    required = (
        ANALYSIS_WINDOW +
        MAX_FORWARD_CANDLES +
        5
    )

    if len(df) < required:

        print()
        print(
            f"WARNING: Need at least {required} candles."
        )

        return

    # --------------------------------------------------------
    # All trades
    # --------------------------------------------------------

    trades = []

    print()
    print("-" * 70)
    print("RUNNING BACKTEST...")
    print("-" * 70)

    # --------------------------------------------------------
    # Historical loop
    # --------------------------------------------------------

    for i in range(
        ANALYSIS_WINDOW,
        len(df) - 1
    ):

        history_start = max(
            0,
            i - ANALYSIS_WINDOW + 1
        )

        history_df = df.iloc[
            history_start:i + 1
        ].copy()

        # ====================================================
        # 5M ANALYSIS
        # ====================================================

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

        # ====================================================
        # ENTRY / SL / TP
        # ====================================================

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

        # ====================================================
        # SIGNAL TIME
        # ====================================================

        signal_time = df[
            "open_time"
        ].iloc[i]

        # ====================================================
        # SESSION
        # ====================================================

        session = get_session(
            signal_time
        )

        # ====================================================
        # SETUP
        # ====================================================

        setup = analysis.get(
            "setup",
            "UNKNOWN"
        )

        liquidity = analysis.get(
            "liquidity_sweep",
            "NONE"
        )

        strength = analysis.get(
            "strength",
            "UNKNOWN"
        )

        adx = analysis.get(
            "adx",
            0.0
        )

        # ====================================================
        # FUTURE CANDLES
        # ====================================================

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

        # ====================================================
        # EVALUATE
        # ====================================================

        result, result_r, bars = evaluate_trade(
            direction=direction,
            entry=float(entry),
            stop_loss=float(stop_loss),
            tp1=float(tp1),
            tp2=float(tp2),
            future_df=future_df
        )

        # ====================================================
        # SAVE
        # ====================================================

        trades.append(
            {
                "time": signal_time,
                "direction": direction,
                "setup": setup,
                "liquidity": liquidity,
                "strength": strength,
                "adx": float(adx),
                "session": session,
                "entry": float(entry),
                "stop_loss": float(stop_loss),
                "tp1": float(tp1),
                "tp2": float(tp2),
                "result": result,
                "r": float(result_r),
                "bars": bars,
            }
        )

    # ========================================================
    # GENERAL STATISTICS
    # ========================================================

    stats = calculate_group_stats(
        trades
    )

    max_drawdown = calculate_max_drawdown(
        trades
    )

    print()
    print("=" * 70)
    print("GENERAL RESULTS")
    print("=" * 70)

    print(
        f"TOTAL SIGNALS : {stats['signals']}"
    )

    print(
        f"WINS           : {stats['wins']}"
    )

    print(
        f"LOSSES         : {stats['losses']}"
    )

    print(
        f"OPEN           : {stats['open']}"
    )

    print(
        f"WIN RATE       : {stats['win_rate']:.2f}%"
    )

    print(
        f"TOTAL R        : {stats['total_r']:+.2f}"
    )

    print(
        f"AVERAGE R      : {stats['avg_r']:+.3f}"
    )

    print(
        f"PROFIT FACTOR  : {stats['profit_factor']:.3f}"
    )

    print(
        f"MAX DRAWDOWN   : {max_drawdown:.2f}R"
    )

    # ========================================================
    # DIRECTION STATISTICS
    # ========================================================

    print()
    print("-" * 70)
    print("DIRECTION STATISTICS")
    print("-" * 70)

    for direction in (
        "BUY",
        "SELL"
    ):

        group = [
            trade
            for trade in trades
            if trade["direction"] == direction
        ]

        s = calculate_group_stats(
            group
        )

        print()
        print(direction)

        print(
            f"  Signals      : {s['signals']}"
        )

        print(
            f"  Wins         : {s['wins']}"
        )

        print(
            f"  Losses       : {s['losses']}"
        )

        print(
            f"  Win Rate     : {s['win_rate']:.2f}%"
        )

        print(
            f"  Total R      : {s['total_r']:+.2f}"
        )

        print(
            f"  Average R    : {s['avg_r']:+.3f}"
        )

        print(
            f"  Profit Factor: {s['profit_factor']:.3f}"
        )

    # ========================================================
    # SETUP STATISTICS
    # ========================================================

    print()
    print("-" * 70)
    print("SETUP STATISTICS")
    print("-" * 70)

    setup_groups = defaultdict(list)

    for trade in trades:

        setup_groups[
            trade["setup"]
        ].append(
            trade
        )

    for setup in sorted(
        setup_groups.keys()
    ):

        group = setup_groups[
            setup
        ]

        s = calculate_group_stats(
            group
        )

        print()
        print(setup)

        print(
            f"  Signals      : {s['signals']}"
        )

        print(
            f"  Win Rate     : {s['win_rate']:.2f}%"
        )

        print(
            f"  Total R      : {s['total_r']:+.2f}"
        )

        print(
            f"  Average R    : {s['avg_r']:+.3f}"
        )

        print(
            f"  Profit Factor: {s['profit_factor']:.3f}"
        )

    # ========================================================
    # LIQUIDITY STATISTICS
    # ========================================================

    print()
    print("-" * 70)
    print("LIQUIDITY SWEEP STATISTICS")
    print("-" * 70)

    liquidity_groups = defaultdict(list)

    for trade in trades:

        liquidity_groups[
            trade["liquidity"]
        ].append(
            trade
        )

    for liquidity in sorted(
        liquidity_groups.keys()
    ):

        group = liquidity_groups[
            liquidity
        ]

        s = calculate_group_stats(
            group
        )

        print()
        print(liquidity)

        print(
            f"  Signals      : {s['signals']}"
        )

        print(
            f"  Win Rate     : {s['win_rate']:.2f}%"
        )

        print(
            f"  Total R      : {s['total_r']:+.2f}"
        )

        print(
            f"  Average R    : {s['avg_r']:+.3f}"
        )

    # ========================================================
    # SESSION STATISTICS
    # ========================================================

    print()
    print("-" * 70)
    print("SESSION STATISTICS (UTC)")
    print("-" * 70)

    session_groups = defaultdict(list)

    for trade in trades:

        session_groups[
            trade["session"]
        ].append(
            trade
        )

    for session in (
        "ASIA",
        "LONDON",
        "NEW_YORK",
        "OFF_SESSION"
    ):

        group = session_groups.get(
            session,
            []
        )

        s = calculate_group_stats(
            group
        )

        print()
        print(session)

        print(
            f"  Signals      : {s['signals']}"
        )

        print(
            f"  Win Rate     : {s['win_rate']:.2f}%"
        )

        print(
            f"  Total R      : {s['total_r']:+.2f}"
        )

        print(
            f"  Average R    : {s['avg_r']:+.3f}"
        )

    # ========================================================
    # STRENGTH STATISTICS
    # ========================================================

    print()
    print("-" * 70)
    print("STRENGTH STATISTICS")
    print("-" * 70)

    strength_groups = defaultdict(list)

    for trade in trades:

        strength_groups[
            trade["strength"]
        ].append(
            trade
        )

    for strength in sorted(
        strength_groups.keys()
    ):

        group = strength_groups[
            strength
        ]

        s = calculate_group_stats(
            group
        )

        print()
        print(strength)

        print(
            f"  Signals      : {s['signals']}"
        )

        print(
            f"  Win Rate     : {s['win_rate']:.2f}%"
        )

        print(
            f"  Total R      : {s['total_r']:+.2f}"
        )

    # ========================================================
    # CONSECUTIVE LOSSES
    # ========================================================

    max_loss_streak = 0
    current_loss_streak = 0

    for trade in trades:

        if trade["result"] == "SL":

            current_loss_streak += 1

            max_loss_streak = max(
                max_loss_streak,
                current_loss_streak
            )

        else:

            current_loss_streak = 0

    print()
    print("-" * 70)
    print("RISK STATISTICS")
    print("-" * 70)

    print(
        f"MAX CONSECUTIVE SL : {max_loss_streak}"
    )

    # ========================================================
    # LAST 15 TRADES
    # ========================================================

    print()
    print("-" * 70)
    print("LAST 15 TRADES")
    print("-" * 70)

    for trade in trades[-15:]:

        print(
            f"{trade['time']} | "
            f"{trade['direction']:4} | "
            f"{trade['setup'][:28]:28} | "
            f"{trade['session']:9} | "
            f"{trade['result']:4} | "
            f"{trade['r']:+.1f}R"
        )

    print()
    print("=" * 70)
    print("5M BACKTEST V3 FINISHED")
    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_backtest()
