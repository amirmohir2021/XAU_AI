# ============================================================
# XAU/USD 5M BACKTEST V4
# ============================================================
#
# V4:
#   5M scalping analysis
#   +
#   5M Entry / SL / TP
#   +
#   1D / 4H / 1H / 15M HTF direction
#
# IMPORTANT:
#   - No lookahead
#   - Only candles available at signal time are used
#   - HTF indicators are calculated before reading them
#   - Main trend requires 3/4 HTF agreement
#   - 5M is used for entry timing
#   - HTF determines the main direction
#
# ============================================================

from collections import Counter

import numpy as np
import pandas as pd


# ============================================================
# PROJECT IMPORTS
# ============================================================

from memory.history import (
    get_5m_candles,
    get_15m_candles,
    get_1h_candles,
    get_4h_candles,
    get_1d_candles,
)

from analysis.analyzer import calculate_indicators
from analysis.indicators import get_latest_indicator_values
from analysis.signal_engine import get_indicator_direction

from analysis.scalping_5m import analyze_5m
from analysis.scalping_levels import generate_scalping_levels


# ============================================================
# SETTINGS
# ============================================================

MIN_5M_CANDLES = 220

HTF_MIN_CANDLES = {
    "1d": 30,
    "4h": 30,
    "1h": 30,
    "15m": 30,
}

HTF_TIMEFRAMES = [
    "1d",
    "4h",
    "1h",
    "15m",
]

TP1_RR = 1.5
TP2_RR = 2.5

MAX_FORWARD_CANDLES = 1000


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        value = float(value)

        if not np.isfinite(value):
            return default

        return value

    except (
        TypeError,
        ValueError,
    ):

        return default


def normalize_direction(direction):

    if direction is None:
        return "NEUTRAL"

    direction = str(
        direction
    ).upper().strip()

    if direction in (
        "BUY",
        "BULLISH",
    ):
        return "BULLISH"

    if direction in (
        "SELL",
        "BEARISH",
    ):
        return "BEARISH"

    return "NEUTRAL"


def normalize_trade_direction(direction):

    if direction is None:
        return None

    direction = str(
        direction
    ).upper().strip()

    if direction in (
        "BUY",
        "BULLISH",
    ):
        return "BUY"

    if direction in (
        "SELL",
        "BEARISH",
    ):
        return "SELL"

    return None


# ============================================================
# DATAFRAME PREPARATION
# ============================================================

def prepare_dataframe(df):

    if df is None:
        return pd.DataFrame()

    df = df.copy()

    if df.empty:
        return df

    if "open_time" in df.columns:

        df["open_time"] = pd.to_datetime(
            df["open_time"],
            utc=True,
            errors="coerce",
        )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "tick_volume",
        "is_open",
    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    if "is_open" not in df.columns:

        df["is_open"] = 0

    df = df.dropna(
        subset=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
        ]
    )

    df = df.sort_values(
        "open_time"
    )

    df = df.drop_duplicates(
        subset=["open_time"],
        keep="last",
    )

    df = df.reset_index(
        drop=True
    )

    return df


# ============================================================
# GET CLOSED HTF CANDLES
# ============================================================

def get_closed_htf_data(
    df,
    timestamp,
):

    if df is None or df.empty:

        return pd.DataFrame()

    timestamp = pd.to_datetime(
        timestamp,
        utc=True,
    )

    closed = df[
        (
            df["open_time"]
            <= timestamp
        )
        &
        (
            df["is_open"] == 0
        )
    ].copy()

    closed = closed.sort_values(
        "open_time"
    )

    closed = closed.reset_index(
        drop=True
    )

    return closed


# ============================================================
# HTF DIRECTION
# ============================================================

def calculate_htf_direction(
    df,
    timestamp,
    timeframe,
):

    try:

        closed = get_closed_htf_data(
            df,
            timestamp,
        )

        minimum = HTF_MIN_CANDLES.get(
            timeframe,
            30,
        )

        if len(closed) < minimum:

            return {
                "direction": "NEUTRAL",
                "strength": "WEAK",
                "bullish_score": 0,
                "bearish_score": 0,
                "adx": 0.0,
                "reasons": [],
            }

        # ----------------------------------------------------
        # IMPORTANT FIX
        #
        # Raw candles do NOT contain EMA20, EMA50, etc.
        #
        # First calculate indicators.
        # ----------------------------------------------------

        indicator_df = calculate_indicators(
            closed
        )

        if indicator_df is None:
            raise ValueError(
                "calculate_indicators returned None"
            )

        if indicator_df.empty:
            raise ValueError(
                "Indicator dataframe is empty"
            )

        # ----------------------------------------------------
        # Remove rows where the indicators needed by
        # V3.1 direction engine are unavailable.
        # ----------------------------------------------------

        required_columns = [
            "EMA20",
            "EMA50",
            "RSI14",
            "MACD",
            "MACD_SIGNAL",
            "ADX14",
            "DI_PLUS",
            "DI_MINUS",
        ]

        existing_columns = [
            column
            for column in required_columns
            if column in indicator_df.columns
        ]

        if not existing_columns:

            raise ValueError(
                "Required indicator columns "
                "were not created"
            )

        indicator_df = indicator_df.dropna(
            subset=existing_columns,
            how="any",
        )

        if indicator_df.empty:

            return {
                "direction": "NEUTRAL",
                "strength": "WEAK",
                "bullish_score": 0,
                "bearish_score": 0,
                "adx": 0.0,
                "reasons": [
                    "No valid indicator values"
                ],
            }

        # ----------------------------------------------------
        # NOW it is safe to call:
        #
        # get_latest_indicator_values()
        # ----------------------------------------------------

        indicators = (
            get_latest_indicator_values(
                indicator_df
            )
        )

        # ----------------------------------------------------
        # USE THE SAME V3.1 DIRECTION ENGINE
        # ----------------------------------------------------

        result = get_indicator_direction(
            indicators
        )

        return {
            "direction": normalize_direction(
                result.get(
                    "direction"
                )
            ),

            "strength": result.get(
                "strength",
                "WEAK",
            ),

            "bullish_score": safe_float(
                result.get(
                    "bullish_score",
                    0,
                )
            ),

            "bearish_score": safe_float(
                result.get(
                    "bearish_score",
                    0,
                )
            ),

            "adx": safe_float(
                result.get(
                    "adx",
                    0,
                )
            ),

            "reasons": result.get(
                "reasons",
                [],
            ),

            "indicators": indicators,
        }

    except Exception as error:

        print(
            f"HTF analysis error "
            f"[{timeframe}]: {error}"
        )

        return {
            "direction": "NEUTRAL",
            "strength": "WEAK",
            "bullish_score": 0,
            "bearish_score": 0,
            "adx": 0.0,
            "reasons": [
                f"ERROR: {error}"
            ],
        }


# ============================================================
# ALL HTF ANALYSIS
# ============================================================

def calculate_all_htf(
    data,
    timestamp,
):

    results = {}

    for timeframe in HTF_TIMEFRAMES:

        results[timeframe] = (
            calculate_htf_direction(
                data[timeframe],
                timestamp,
                timeframe,
            )
        )

    return results


# ============================================================
# MAIN HTF TREND
# ============================================================

def determine_main_htf_trend(
    htf_results,
):

    directions = [
        htf_results[tf]["direction"]
        for tf in HTF_TIMEFRAMES
    ]

    bullish = directions.count(
        "BULLISH"
    )

    bearish = directions.count(
        "BEARISH"
    )

    neutral = directions.count(
        "NEUTRAL"
    )

    # --------------------------------------------------------
    # 3/4 or 4/4 = MAIN TREND
    # --------------------------------------------------------

    if bullish >= 3:

        return (
            "BULLISH",
            bullish,
            bearish,
            neutral,
        )

    if bearish >= 3:

        return (
            "BEARISH",
            bullish,
            bearish,
            neutral,
        )

    return (
        "MIXED",
        bullish,
        bearish,
        neutral,
    )


# ============================================================
# 5M ALIGNMENT
# ============================================================

def determine_alignment(
    main_trend,
    direction_5m,
):

    if (
        main_trend == "BULLISH"
        and direction_5m == "BULLISH"
    ):

        return "TREND_ALIGNED"

    if (
        main_trend == "BEARISH"
        and direction_5m == "BEARISH"
    ):

        return "TREND_ALIGNED"

    if (
        main_trend == "BULLISH"
        and direction_5m == "BEARISH"
    ):

        return "COUNTER_TREND"

    if (
        main_trend == "BEARISH"
        and direction_5m == "BULLISH"
    ):

        return "COUNTER_TREND"

    return "NO_TREND"


# ============================================================
# GET 5M ANALYSIS
# ============================================================

def analyze_5m_at_index(
    df_5m,
    index,
):

    if index < MIN_5M_CANDLES:

        return None

    # --------------------------------------------------------
    # NO LOOKAHEAD
    #
    # At index X the engine sees only:
    #
    # 0 ... X
    #
    # It cannot see X+1, X+2...
    # --------------------------------------------------------

    history = df_5m.iloc[
        :index + 1
    ].copy()

    if len(history) < MIN_5M_CANDLES:

        return None

    try:

        result = analyze_5m(
            history
        )

        return result

    except Exception as error:

        print(
            f"5M analysis error: {error}"
        )

        return None


# ============================================================
# 5M ENTRY / SL / TP
# ============================================================

def get_scalping_levels(
    df_5m,
    index,
    analysis_5m,
):

    try:

        # ----------------------------------------------------
        # IMPORTANT FIX
        #
        # generate_scalping_levels()
        # must receive the historical 5M dataframe
        # AND the 5M analysis.
        # ----------------------------------------------------

        history = df_5m.iloc[
            :index + 1
        ].copy()

        levels = generate_scalping_levels(
            history,
            analysis_5m,
        )

        if not isinstance(
            levels,
            dict,
        ):

            return None

        return levels

    except Exception as error:

        print(
            f"5M levels error: {error}"
        )

        return None


# ============================================================
# TRADE RESULT
# ============================================================

def evaluate_trade(
    df_5m,
    signal_index,
    direction,
    entry,
    stop_loss,
    tp1,
    tp2,
):

    entry = safe_float(
        entry,
        np.nan,
    )

    stop_loss = safe_float(
        stop_loss,
        np.nan,
    )

    tp1 = safe_float(
        tp1,
        np.nan,
    )

    tp2 = safe_float(
        tp2,
        np.nan,
    )

    if not all(
        np.isfinite(value)
        for value in (
            entry,
            stop_loss,
            tp1,
            tp2,
        )
    ):

        return {
            "result": "INVALID",
            "r": 0.0,
            "bars": 0,
        }

    risk = abs(
        entry - stop_loss
    )

    if risk <= 0:

        return {
            "result": "INVALID",
            "r": 0.0,
            "bars": 0,
        }

    end_index = min(
        len(df_5m),
        signal_index
        + 1
        + MAX_FORWARD_CANDLES,
    )

    for future_index in range(
        signal_index + 1,
        end_index,
    ):

        candle = df_5m.iloc[
            future_index
        ]

        high = safe_float(
            candle["high"]
        )

        low = safe_float(
            candle["low"]
        )

        bars = (
            future_index
            - signal_index
        )

        # ====================================================
        # BUY
        # ====================================================

        if direction == "BUY":

            sl_hit = (
                low <= stop_loss
            )

            tp2_hit = (
                high >= tp2
            )

            tp1_hit = (
                high >= tp1
            )

            # ------------------------------------------------
            # CONSERVATIVE RULE:
            #
            # If SL and TP happen inside same candle,
            # SL is assumed to happen first.
            # ------------------------------------------------

            if sl_hit:

                return {
                    "result": "SL",
                    "r": -1.0,
                    "bars": bars,
                }

            if tp2_hit:

                return {
                    "result": "TP2",
                    "r": TP2_RR,
                    "bars": bars,
                }

            if tp1_hit:

                return {
                    "result": "TP1",
                    "r": TP1_RR,
                    "bars": bars,
                }

        # ====================================================
        # SELL
        # ====================================================

        elif direction == "SELL":

            sl_hit = (
                high >= stop_loss
            )

            tp2_hit = (
                low <= tp2
            )

            tp1_hit = (
                low <= tp1
            )

            # Conservative SL-first rule

            if sl_hit:

                return {
                    "result": "SL",
                    "r": -1.0,
                    "bars": bars,
                }

            if tp2_hit:

                return {
                    "result": "TP2",
                    "r": TP2_RR,
                    "bars": bars,
                }

            if tp1_hit:

                return {
                    "result": "TP1",
                    "r": TP1_RR,
                    "bars": bars,
                }

    # No TP/SL hit within test horizon

    return {
        "result": "OPEN",
        "r": 0.0,
        "bars": (
            end_index
            - signal_index
        ),
    }


# ============================================================
# PROFIT FACTOR
# ============================================================

def calculate_profit_factor(
    trades,
):

    gross_profit = sum(
        max(
            safe_float(
                trade["r"]
            ),
            0.0,
        )
        for trade in trades
    )

    gross_loss = abs(
        sum(
            min(
                safe_float(
                    trade["r"]
                ),
                0.0,
            )
            for trade in trades
        )
    )

    if gross_loss == 0:

        if gross_profit > 0:
            return float("inf")

        return 0.0

    return (
        gross_profit
        / gross_loss
    )


# ============================================================
# MAX DRAWDOWN
# ============================================================

def calculate_max_drawdown(
    trades,
):

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for trade in trades:

        equity += safe_float(
            trade["r"]
        )

        peak = max(
            peak,
            equity,
        )

        drawdown = (
            peak - equity
        )

        if drawdown > max_drawdown:

            max_drawdown = drawdown

    return max_drawdown


# ============================================================
# PRINT DIRECTION STATISTICS
# ============================================================

def print_direction_statistics(
    trades,
):

    print()
    print("-" * 70)
    print("TRADE DIRECTION")
    print("-" * 70)

    for direction in (
        "BUY",
        "SELL",
    ):

        subset = [
            trade
            for trade in trades
            if trade["direction"]
            == direction
        ]

        total = len(
            subset
        )

        wins = sum(
            1
            for trade in subset
            if trade["result"]
            in (
                "TP1",
                "TP2",
            )
        )

        losses = sum(
            1
            for trade in subset
            if trade["result"]
            == "SL"
        )

        closed = (
            wins + losses
        )

        win_rate = (
            wins / closed * 100
            if closed > 0
            else 0.0
        )

        total_r = sum(
            safe_float(
                trade["r"]
            )
            for trade in subset
        )

        pf = calculate_profit_factor(
            subset
        )

        if np.isinf(pf):

            pf_text = "INF"

        else:

            pf_text = f"{pf:.3f}"

        print(
            f"{direction:<5} "
            f"{total:>4} | "
            f"W {wins:>3} | "
            f"L {losses:>3} | "
            f"WR {win_rate:>6.2f}% | "
            f"R {total_r:+.2f} | "
            f"PF {pf_text}"
        )


# ============================================================
# PRINT SETUP STATISTICS
# ============================================================

def print_setup_statistics(
    trades,
):

    print()
    print("-" * 70)
    print("SETUP RESULTS")
    print("-" * 70)

    setup_names = sorted(
        set(
            trade["setup"]
            for trade in trades
        )
    )

    for setup in setup_names:

        subset = [
            trade
            for trade in trades
            if trade["setup"]
            == setup
        ]

        total = len(
            subset
        )

        wins = sum(
            1
            for trade in subset
            if trade["result"]
            in (
                "TP1",
                "TP2",
            )
        )

        losses = sum(
            1
            for trade in subset
            if trade["result"]
            == "SL"
        )

        closed = (
            wins + losses
        )

        win_rate = (
            wins / closed * 100
            if closed > 0
            else 0.0
        )

        total_r = sum(
            safe_float(
                trade["r"]
            )
            for trade in subset
        )

        pf = calculate_profit_factor(
            subset
        )

        if np.isinf(pf):

            pf_text = "INF"

        else:

            pf_text = f"{pf:.3f}"

        print(
            f"{setup:<32} "
            f"{total:>4} | "
            f"W {wins:>3} | "
            f"L {losses:>3} | "
            f"WR {win_rate:>6.2f}% | "
            f"R {total_r:+.2f} | "
            f"PF {pf_text}"
        )


# ============================================================
# MAIN BACKTEST
# ============================================================

def run_backtest():

    print()
    print("=" * 70)
    print("XAU/USD 5M SCALPING BACKTEST V4")
    print("V3.1 MULTI-TIMEFRAME TREND INTELLIGENCE")
    print("=" * 70)

    # ========================================================
    # LOAD DATA
    # ========================================================

    print()
    print("Loading historical data...")

    df_5m = prepare_dataframe(
        get_5m_candles(
            limit=1000
        )
    )

    df_15m = prepare_dataframe(
        get_15m_candles(
            limit=1000
        )
    )

    df_1h = prepare_dataframe(
        get_1h_candles(
            limit=1000
        )
    )

    df_4h = prepare_dataframe(
        get_4h_candles(
            limit=1000
        )
    )

    df_1d = prepare_dataframe(
        get_1d_candles(
            limit=1000
        )
    )

    print(
        f"5M  : {len(df_5m)}"
    )

    print(
        f"15M : {len(df_15m)}"
    )

    print(
        f"1H  : {len(df_1h)}"
    )

    print(
        f"4H  : {len(df_4h)}"
    )

    print(
        f"1D  : {len(df_1d)}"
    )

    # ========================================================
    # CHECK 5M DATA
    # ========================================================

    if len(df_5m) < MIN_5M_CANDLES:

        print()
        print(
            "ERROR: Not enough 5M candles."
        )

        print(
            f"Required: "
            f"{MIN_5M_CANDLES}"
        )

        print(
            f"Available: "
            f"{len(df_5m)}"
        )

        return

    data = {
        "5m": df_5m,
        "15m": df_15m,
        "1h": df_1h,
        "4h": df_4h,
        "1d": df_1d,
    }

    # ========================================================
    # PERIOD
    # ========================================================

    if not df_5m.empty:

        print()

        print(
            "Period: "
            f"{df_5m.iloc[0]['open_time']} "
            "-> "
            f"{df_5m.iloc[-1]['open_time']}"
        )

    # ========================================================
    # STATISTICS
    # ========================================================

    all_5m_signals = 0

    trend_aligned_count = 0
    counter_trend_count = 0
    no_trend_count = 0

    main_trend_counter = Counter()

    htf_agreement_counter = Counter()

    setup_counter = Counter()

    trades = []

    # ========================================================
    # RUN BACKTEST
    # ========================================================

    print()
    print(
        "Running multi-timeframe backtest..."
    )

    print()

    for index in range(
        MIN_5M_CANDLES,
        len(df_5m),
    ):

        # ----------------------------------------------------
        # CURRENT 5M TIMESTAMP
        # ----------------------------------------------------

        timestamp = df_5m.iloc[
            index
        ]["open_time"]

        # ----------------------------------------------------
        # 5M ANALYSIS
        # ----------------------------------------------------

        analysis_5m = (
            analyze_5m_at_index(
                df_5m,
                index,
            )
        )

        if not analysis_5m:

            continue

        all_5m_signals += 1

        direction_5m = normalize_direction(
            analysis_5m.get(
                "direction"
            )
        )

        setup = str(
            analysis_5m.get(
                "setup",
                "NONE",
            )
        )

        setup_counter[
            setup
        ] += 1

        # ----------------------------------------------------
        # HTF ANALYSIS
        # ----------------------------------------------------

        htf_results = (
            calculate_all_htf(
                data,
                timestamp,
            )
        )

        # ----------------------------------------------------
        # MAIN HTF TREND
        # ----------------------------------------------------

        (
            main_trend,
            bullish_count,
            bearish_count,
            neutral_count,
        ) = determine_main_htf_trend(
            htf_results
        )

        main_trend_counter[
            main_trend
        ] += 1

        agreement_count = max(
            bullish_count,
            bearish_count,
        )

        htf_agreement_counter[
            f"{agreement_count}/4"
        ] += 1

        # ----------------------------------------------------
        # ALIGNMENT
        # ----------------------------------------------------

        alignment = determine_alignment(
            main_trend,
            direction_5m,
        )

        if alignment == "TREND_ALIGNED":

            trend_aligned_count += 1

        elif alignment == "COUNTER_TREND":

            counter_trend_count += 1

        else:

            no_trend_count += 1

        # ----------------------------------------------------
        # ONLY TREND-ALIGNED SETUPS
        #
        # HTF determines main direction.
        # 5M determines entry timing.
        # ----------------------------------------------------

        if alignment != "TREND_ALIGNED":

            continue

        # ----------------------------------------------------
        # GET 5M ENTRY / SL / TP
        # ----------------------------------------------------

        levels = get_scalping_levels(
            df_5m,
            index,
            analysis_5m,
        )

        if not levels:

            continue

        # ----------------------------------------------------
        # STATUS MUST BE READY
        # ----------------------------------------------------

        status = str(
            levels.get(
                "status",
                "WAIT",
            )
        ).upper()

        if status != "READY":

            continue

        # ----------------------------------------------------
        # EXTRACT LEVELS
        # ----------------------------------------------------

        direction = normalize_trade_direction(
            levels.get(
                "direction"
            )
        )

        entry = safe_float(
            levels.get(
                "entry"
            ),
            np.nan,
        )

        stop_loss = safe_float(
            levels.get(
                "stop_loss"
            ),
            np.nan,
        )

        tp1 = safe_float(
            levels.get(
                "tp1"
            ),
            np.nan,
        )

        tp2 = safe_float(
            levels.get(
                "tp2"
            ),
            np.nan,
        )

        # ----------------------------------------------------
        # VALIDATE
        # ----------------------------------------------------

        if direction is None:

            continue

        if not all(
            np.isfinite(value)
            for value in (
                entry,
                stop_loss,
                tp1,
                tp2,
            )
        ):

            continue

        # ----------------------------------------------------
        # 5M DIRECTION MUST MATCH TRADE
        # ----------------------------------------------------

        if (
            direction == "BUY"
            and direction_5m
            != "BULLISH"
        ):

            continue

        if (
            direction == "SELL"
            and direction_5m
            != "BEARISH"
        ):

            continue

        # ----------------------------------------------------
        # MAIN HTF TREND MUST MATCH TRADE
        # ----------------------------------------------------

        if (
            direction == "BUY"
            and main_trend
            != "BULLISH"
        ):

            continue

        if (
            direction == "SELL"
            and main_trend
            != "BEARISH"
        ):

            continue

        # ----------------------------------------------------
        # EVALUATE FUTURE
        # ----------------------------------------------------

        result = evaluate_trade(
            df_5m,
            index,
            direction,
            entry,
            stop_loss,
            tp1,
            tp2,
        )

        # ----------------------------------------------------
        # SAVE TRADE
        # ----------------------------------------------------

        trade = {
            "timestamp": timestamp,

            "direction": direction,

            "entry": entry,

            "stop_loss": stop_loss,

            "tp1": tp1,

            "tp2": tp2,

            "result": result[
                "result"
            ],

            "r": result[
                "r"
            ],

            "bars": result[
                "bars"
            ],

            "setup": setup,

            "direction_5m":
                direction_5m,

            "main_trend":
                main_trend,

            "alignment":
                alignment,

            "htf_1d":
                htf_results[
                    "1d"
                ]["direction"],

            "htf_4h":
                htf_results[
                    "4h"
                ]["direction"],

            "htf_1h":
                htf_results[
                    "1h"
                ]["direction"],

            "htf_15m":
                htf_results[
                    "15m"
                ]["direction"],

            "htf_agreement":
                agreement_count,
        }

        trades.append(
            trade
        )

    # ========================================================
    # FINAL RESULTS
    # ========================================================

    print()
    print("=" * 70)
    print("V4 BACKTEST RESULTS")
    print("=" * 70)

    # ========================================================
    # ALL 5M SIGNALS
    # ========================================================

    print()
    print(
        "5M SIGNAL OVERVIEW"
    )

    print(
        f"TOTAL 5M SIGNALS : "
        f"{all_5m_signals}"
    )

    print(
        f"TREND ALIGNED    : "
        f"{trend_aligned_count}"
    )

    print(
        f"COUNTER TREND    : "
        f"{counter_trend_count}"
    )

    print(
        f"NO CLEAR HTF     : "
        f"{no_trend_count}"
    )

    # ========================================================
    # TRADE RESULTS
    # ========================================================

    total = len(
        trades
    )

    wins = sum(
        1
        for trade in trades
        if trade["result"]
        in (
            "TP1",
            "TP2",
        )
    )

    losses = sum(
        1
        for trade in trades
        if trade["result"]
        == "SL"
    )

    open_trades = sum(
        1
        for trade in trades
        if trade["result"]
        == "OPEN"
    )

    invalid = sum(
        1
        for trade in trades
        if trade["result"]
        == "INVALID"
    )

    closed = (
        wins + losses
    )

    win_rate = (
        wins / closed * 100
        if closed > 0
        else 0.0
    )

    total_r = sum(
        safe_float(
            trade["r"]
        )
        for trade in trades
    )

    average_r = (
        total_r / total
        if total > 0
        else 0.0
    )

    profit_factor = (
        calculate_profit_factor(
            trades
        )
    )

    max_drawdown = (
        calculate_max_drawdown(
            trades
        )
    )

    print()
    print(
        "ALL TREND-ALIGNED TRADES"
    )

    print(
        f"Signals       : {total}"
    )

    print(
        f"Wins          : {wins}"
    )

    print(
        f"Losses        : {losses}"
    )

    print(
        f"Open          : {open_trades}"
    )

    print(
        f"Invalid       : {invalid}"
    )

    print(
        f"Closed        : {closed}"
    )

    print(
        f"Win Rate      : "
        f"{win_rate:.2f}%"
    )

    print(
        f"Total R       : "
        f"{total_r:+.2f}"
    )

    print(
        f"Average R     : "
        f"{average_r:+.3f}"
    )

    if np.isinf(
        profit_factor
    ):

        print(
            "Profit Factor : INF"
        )

    else:

        print(
            f"Profit Factor : "
            f"{profit_factor:.3f}"
        )

    print(
        f"Max Drawdown  : "
        f"{max_drawdown:.2f}R"
    )

    # ========================================================
    # HTF ALIGNMENT
    # ========================================================

    print()
    print("-" * 70)
    print("HTF / 5M ALIGNMENT")
    print("-" * 70)

    print(
        f"TREND ALIGNED : "
        f"{trend_aligned_count}"
    )

    print(
        f"COUNTER TREND : "
        f"{counter_trend_count}"
    )

    print(
        f"NO CLEAR HTF TREND: "
        f"{no_trend_count}"
    )

    # ========================================================
    # MAIN TREND
    # ========================================================

    print()
    print("-" * 70)
    print("MAIN HTF TREND")
    print("-" * 70)

    print(
        f"MAIN TREND BULLISH: "
        f"{main_trend_counter['BULLISH']}"
    )

    print(
        f"MAIN TREND BEARISH: "
        f"{main_trend_counter['BEARISH']}"
    )

    print(
        f"MAIN TREND MIXED: "
        f"{main_trend_counter['MIXED']}"
    )

    # ========================================================
    # HTF AGREEMENT
    # ========================================================

    print()
    print("-" * 70)
    print("HTF AGREEMENT")
    print("-" * 70)

    for value in (
        "4/4",
        "3/4",
        "2/4",
        "1/4",
        "0/4",
    ):

        print(
            f"HTF AGREEMENT {value}: "
            f"{htf_agreement_counter[value]}"
        )

    # ========================================================
    # SETUPS
    # ========================================================

    print()
    print("-" * 70)
    print("5M SETUPS")
    print("-" * 70)

    for setup, count in (
        setup_counter.most_common()
    ):

        print(
            f"{setup:<32} "
            f"{count}"
        )

    # ========================================================
    # TRADE DIRECTION
    # ========================================================

    print_direction_statistics(
        trades
    )

    # ========================================================
    # SETUP RESULTS
    # ========================================================

    if trades:

        print_setup_statistics(
            trades
        )

    # ========================================================
    # RECENT TRADES
    # ========================================================

    print()
    print("-" * 70)
    print("RECENT TRADES")
    print("-" * 70)

    if not trades:

        print(
            "No completed READY trades."
        )

    else:

        for trade in trades[-15:]:

            timestamp = trade[
                "timestamp"
            ]

            if hasattr(
                timestamp,
                "strftime",
            ):

                time_text = (
                    timestamp.strftime(
                        "%Y-%m-%d %H:%M"
                    )
                )

            else:

                time_text = str(
                    timestamp
                )

            print(
                f"{time_text} | "
                f"{trade['direction']:<4} | "
                f"HTF {trade['main_trend']:<7} | "
                f"{trade['setup']:<30} | "
                f"{trade['result']:<4} | "
                f"{trade['r']:+.2f}R"
            )

    # ========================================================
    # LAST HTF SNAPSHOT
    # ========================================================

    print()
    print("-" * 70)
    print("LATEST HTF SNAPSHOT")
    print("-" * 70)

    if not df_5m.empty:

        latest_timestamp = (
            df_5m.iloc[-1][
                "open_time"
            ]
        )

        latest_htf = (
            calculate_all_htf(
                data,
                latest_timestamp,
            )
        )

        for timeframe in (
            "1d",
            "4h",
            "1h",
            "15m",
        ):

            item = latest_htf[
                timeframe
            ]

            print(
                f"{timeframe.upper():<3} : "
                f"{item['direction']:<8} | "
                f"Strength: "
                f"{item['strength']:<8} | "
                f"Bull: "
                f"{item['bullish_score']:.0f} | "
                f"Bear: "
                f"{item['bearish_score']:.0f} | "
                f"ADX: "
                f"{item['adx']:.2f}"
            )

    # ========================================================
    # FINISHED
    # ========================================================

    print()
    print("=" * 70)
    print("BACKTEST V4 FINISHED")
    print("=" * 70)

    print(
        "No-lookahead HTF analysis: ENABLED"
    )

    print(
        "5M Entry/SL/TP engine: ENABLED"
    )

    print(
        "3/4 HTF main trend filter: ENABLED"
    )

    print(
        "Conservative SL-first rule: ENABLED"
    )

    print(
        "Results are historical backtest "
        "statistics, not guaranteed future performance."
    )

    print(
        "=" * 70
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    run_backtest()