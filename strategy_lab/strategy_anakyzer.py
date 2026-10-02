from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from data.market_data import get_xauusd_candles
from analysis.indicators import (
    calculate_indicators,
    get_latest_indicator_values,
)
from analysis.structure import analyze_structure
from analysis.scalping_5m import analyze_5m
from analysis.signal_engine import generate_signal


# ============================================================
# SETTINGS
# ============================================================

MIN_5M_CANDLES = 220

HTF_LIMIT = 250

PRINT_SWEEP_DETAILS = True


# ============================================================
# TIME
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


# ============================================================
# DATA NORMALIZATION
# ============================================================

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize BiQuote API column names.

    API:
        openTime
        isOpen

    Internal:
        open_time
        is_open
    """

    df = df.copy()

    rename_map = {}

    if "openTime" in df.columns:
        rename_map["openTime"] = "open_time"

    if "isOpen" in df.columns:
        rename_map["isOpen"] = "is_open"

    if rename_map:
        df = df.rename(columns=rename_map)

    if "open_time" in df.columns:
        df["open_time"] = pd.to_datetime(
            df["open_time"],
            utc=True,
            errors="coerce",
        )

    return df


# ============================================================
# CLOSED CANDLES ONLY
# ============================================================

def closed_only(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return ONLY closed candles.

    This is a critical no-lookahead protection.
    """

    df = normalize_columns(df)

    if "is_open" in df.columns:
        df = df[df["is_open"] == False].copy()

    return df.reset_index(drop=True)


# ============================================================
# HISTORICAL DATA SLICE
# ============================================================

def slice_before(
    df: pd.DataFrame,
    point_time: pd.Timestamp,
) -> pd.DataFrame:
    """
    Return candles available at the historical point.

    Only candles whose opening time is <= point_time
    are allowed.

    Current/future candles are never used.
    """

    if "open_time" not in df.columns:
        return df.copy()

    result = df[
        df["open_time"] <= point_time
    ].copy()

    return result.reset_index(drop=True)


# ============================================================
# HISTORICAL HTF CONTEXT
# ============================================================

def build_historical_htf_context(
    df_1d: pd.DataFrame,
    df_4h: pd.DataFrame,
    df_1h: pd.DataFrame,
    df_15m: pd.DataFrame,
    point_time: pd.Timestamp,
):
    """
    Build V3.1 HTF context for a historical 5M point.

    IMPORTANT:

    We do NOT call get_htf_context() here.

    get_htf_context() loads current market data and would
    introduce lookahead bias into a historical backtest.

    Instead, each timeframe is sliced at the historical
    point first, then V3.1 is executed on that historical
    data.
    """

    # --------------------------------------------------------
    # Historical slices
    # --------------------------------------------------------

    d1 = slice_before(
        df_1d,
        point_time,
    )

    h4 = slice_before(
        df_4h,
        point_time,
    )

    h1 = slice_before(
        df_1h,
        point_time,
    )

    m15 = slice_before(
        df_15m,
        point_time,
    )

    # --------------------------------------------------------
    # Minimum requirements
    #
    # IMPORTANT:
    # Do NOT require 210 candles on 4H.
    #
    # Current API only provides around 181 4H candles.
    # V3.1 structure can still work with this amount.
    # --------------------------------------------------------

    if len(d1) < 200:
        return None

    if len(h4) < 30:
        return None

    if len(h1) < 30:
        return None

    if len(m15) < 30:
        return None

    # --------------------------------------------------------
    # Limit data size
    # --------------------------------------------------------

    d1 = d1.tail(HTF_LIMIT).copy()
    h4 = h4.tail(HTF_LIMIT).copy()
    h1 = h1.tail(HTF_LIMIT).copy()
    m15 = m15.tail(HTF_LIMIT).copy()

    # --------------------------------------------------------
    # Indicators
    # --------------------------------------------------------

    d1_ind = calculate_indicators(d1)
    h4_ind = calculate_indicators(h4)
    h1_ind = calculate_indicators(h1)
    m15_ind = calculate_indicators(m15)

    d1_values = get_latest_indicator_values(
        d1_ind
    )

    h4_values = get_latest_indicator_values(
        h4_ind
    )

    h1_values = get_latest_indicator_values(
        h1_ind
    )

    m15_values = get_latest_indicator_values(
        m15_ind
    )

    # --------------------------------------------------------
    # 4H Market Structure
    # --------------------------------------------------------

    h4_structure = analyze_structure(
        h4
    )

    # --------------------------------------------------------
    # Exact V3.1 input
    # --------------------------------------------------------

    timeframe_data = {
        "1d": d1_values,
        "4h": h4_values,
        "1h": h1_values,
        "15m": m15_values,
    }

    structure_data = h4_structure

    # --------------------------------------------------------
    # REAL V3.1 ENGINE
    # --------------------------------------------------------

    v31 = generate_signal(
        timeframe_data,
        structure_data,
    )

    # --------------------------------------------------------
    # Extract V3.1 context
    # --------------------------------------------------------

    major_direction = v31.get(
        "major_direction",
        "NEUTRAL",
    )

    structure_direction = v31.get(
        "structure_direction",
        "NEUTRAL",
    )

    h1_direction = v31.get(
        "h1_direction",
        "NEUTRAL",
    )

    m15_direction = v31.get(
        "m15_direction",
        "NEUTRAL",
    )

    directions = [
        major_direction,
        structure_direction,
        h1_direction,
        m15_direction,
    ]

    bullish = directions.count(
        "BULLISH"
    )

    bearish = directions.count(
        "BEARISH"
    )

    # --------------------------------------------------------
    # HTF agreement
    # --------------------------------------------------------

    if bullish >= 3:

        htf_agreement = "BULLISH"

    elif bearish >= 3:

        htf_agreement = "BEARISH"

    elif bullish > bearish:

        htf_agreement = "WEAK_BULLISH"

    elif bearish > bullish:

        htf_agreement = "WEAK_BEARISH"

    else:

        htf_agreement = "MIXED"

    return {
        "status": v31.get(
            "status",
            "WAIT",
        ),

        "signal": v31.get(
            "signal",
            "WAIT",
        ),

        "price": v31.get(
            "price"
        ),

        "confidence": v31.get(
            "confidence",
            0,
        ),

        "confirmations": v31.get(
            "confirmations",
            0,
        ),

        "major_direction": major_direction,

        "structure_direction": structure_direction,

        "h1_direction": h1_direction,

        "m15_direction": m15_direction,

        "market_phase": v31.get(
            "market_phase",
            "NONE",
        ),

        "entry_trigger": v31.get(
            "entry_trigger",
            "NO_TRIGGER",
        ),

        "htf_agreement": htf_agreement,

        "reasons": v31.get(
            "reasons",
            [],
        ),

        "levels": v31.get(
            "levels",
            {},
        ),

        "recent_bos": v31.get(
            "recent_bos"
        ),

        "recent_choch": v31.get(
            "recent_choch"
        ),

        "timeframe_data": timeframe_data,

        "structure_data": structure_data,
    }


# ============================================================
# V3.1 WAIT DIAGNOSTIC
# ============================================================

def diagnose_v31_wait(
    context: dict,
) -> str:
    """
    Explain why V3.1 returned WAIT.

    This function DOES NOT modify V3.1.

    It only classifies the already-produced result.
    """

    signal = context.get(
        "signal",
        "WAIT",
    )

    if signal != "WAIT":
        return "V3.1_SIGNAL_AVAILABLE"

    major = context.get(
        "major_direction",
        "NEUTRAL",
    )

    structure = context.get(
        "structure_direction",
        "NEUTRAL",
    )

    h1 = context.get(
        "h1_direction",
        "NEUTRAL",
    )

    m15 = context.get(
        "m15_direction",
        "NEUTRAL",
    )

    confirmations = int(
        context.get(
            "confirmations",
            0,
        )
    )

    # --------------------------------------------------------
    # Major trend
    # --------------------------------------------------------

    if major == "NEUTRAL":
        return "MAJOR_TREND_NEUTRAL"

    # --------------------------------------------------------
    # 4H structure
    # --------------------------------------------------------

    if structure == "NEUTRAL":
        return "4H_STRUCTURE_NEUTRAL"

    if structure != major:
        return "4H_STRUCTURE_CONFLICT"

    # --------------------------------------------------------
    # 1H
    # --------------------------------------------------------

    if h1 != major:
        return "1H_CONFLICT"

    # --------------------------------------------------------
    # 15M
    # --------------------------------------------------------

    if m15 != major:
        return "15M_CONFLICT"

    # --------------------------------------------------------
    # Confirmations
    # --------------------------------------------------------

    if confirmations < 3:
        return "CONFIRMATIONS_LT_3"

    # --------------------------------------------------------
    # Entry trigger
    # --------------------------------------------------------

    trigger = context.get(
        "entry_trigger",
        "NO_TRIGGER",
    )

    if trigger == "NO_TRIGGER":
        return "ENTRY_TRIGGER_MISSING"

    return "OTHER_V31_WAIT"


# ============================================================
# SWEEP REJECTION DIAGNOSTIC
# ============================================================

def diagnose_sweep_rejection(
    sweep: str,
    v31_context: dict,
    direction_5m: str,
) -> str:
    """
    Reproduce the logical order of the strategy without
    modifying the strategy itself.
    """

    v31_signal = v31_context.get(
        "signal",
        "WAIT",
    )

    # --------------------------------------------------------
    # V3.1 first gate
    # --------------------------------------------------------

    if v31_signal not in (
        "BUY",
        "SELL",
    ):
        return "V3.1_WAIT"

    # --------------------------------------------------------
    # Bullish sweep
    # --------------------------------------------------------

    if sweep == "BULLISH_SWEEP":

        if v31_signal != "BUY":
            return "SWEEP_V31_CONFLICT"

        if direction_5m != "BULLISH":
            return "5M_NOT_BULLISH"

        return "READY_FOR_BUY"

    # --------------------------------------------------------
    # Bearish sweep
    # --------------------------------------------------------

    if sweep == "BEARISH_SWEEP":

        if v31_signal != "SELL":
            return "SWEEP_V31_CONFLICT"

        if direction_5m != "BEARISH":
            return "5M_NOT_BEARISH"

        return "READY_FOR_SELL"

    return "NO_SWEEP"


# ============================================================
# PRINT DETAILED SWEEP TABLE
# ============================================================

def print_sweep_diagnostic(
    sweeps: list[dict],
):

    print()
    print("=" * 120)
    print("LIQUIDITY SWEEP DIAGNOSTIC")
    print("=" * 120)

    if not sweeps:

        print(
            "No liquidity sweeps found."
        )

        return

    print()

    header = (
        f"{'#':>3} "
        f"{'TIME':<25} "
        f"{'SWEEP':<16} "
        f"{'V3.1':<7} "
        f"{'CONF':>4} "
        f"{'1D':<9} "
        f"{'4H':<9} "
        f"{'1H':<9} "
        f"{'15M':<9} "
        f"{'5M':<9} "
        f"REJECTION"
    )

    print(header)

    print("-" * 120)

    for i, item in enumerate(
        sweeps,
        start=1,
    ):

        print(
            f"{i:>3} "
            f"{item['time']:<25} "
            f"{item['sweep']:<16} "
            f"{item['v31_signal']:<7} "
            f"{item['confirmations']:>4} "
            f"{item['1d']:<9} "
            f"{item['4h']:<9} "
            f"{item['1h']:<9} "
            f"{item['15m']:<9} "
            f"{item['5m']:<9} "
            f"{item['rejection']}"
        )

    print("-" * 120)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "XAU_AI LIQUIDITY SWEEP STRATEGY ANALYZER V4.2"
    )
    print("=" * 70)

    print()
    print(
        "Historical test uses ONLY CLOSED candles."
    )

    print(
        "No current/open candle is used for signal generation."
    )

    print()
    print(
        f"Analysis started: {utc_now()}"
    )

    # ========================================================
    # LOAD MARKET DATA
    # ========================================================

    print()
    print(
        "Loading historical market data..."
    )

    df_5m = normalize_columns(
        get_xauusd_candles(
            interval="5m",
            limit=300,
        )
    )

    df_15m = normalize_columns(
        get_xauusd_candles(
            interval="15m",
            limit=250,
        )
    )

    df_1h = normalize_columns(
        get_xauusd_candles(
            interval="1h",
            limit=250,
        )
    )

    df_4h = normalize_columns(
        get_xauusd_candles(
            interval="4h",
            limit=250,
        )
    )

    df_1d = normalize_columns(
        get_xauusd_candles(
            interval="1d",
            limit=500,
        )
    )

    print(
        f"5M   candles: {len(df_5m)}"
    )

    print(
        f"15M  candles: {len(df_15m)}"
    )

    print(
        f"1H   candles: {len(df_1h)}"
    )

    print(
        f"4H   candles: {len(df_4h)}"
    )

    print(
        f"1D   candles: {len(df_1d)}"
    )

    # ========================================================
    # CLOSED DATA
    # ========================================================

    df_5m_closed = closed_only(
        df_5m
    )

    df_15m_closed = closed_only(
        df_15m
    )

    df_1h_closed = closed_only(
        df_1h
    )

    df_4h_closed = closed_only(
        df_4h
    )

    df_1d_closed = closed_only(
        df_1d
    )

    print()
    print(
        f"Closed 5M candles available: "
        f"{len(df_5m_closed)}"
    )

    if len(df_5m_closed) < MIN_5M_CANDLES:

        print()
        print(
            "ERROR: Not enough closed 5M candles."
        )

        return

    # ========================================================
    # HISTORICAL ANALYSIS
    # ========================================================

    print()
    print(
        "Running REAL V3.1 + Liquidity Sweep "
        "NO-LOOKAHEAD analysis..."
    )

    start_index = (
        MIN_5M_CANDLES - 1
    )

    total_points = (
        len(df_5m_closed)
        - start_index
    )

    print()
    print(
        f"Historical points to process: "
        f"{total_points}"
    )

    results = []

    sweep_diagnostics = []

    # ========================================================
    # HISTORICAL LOOP
    # ========================================================

    for i in range(
        start_index,
        len(df_5m_closed),
    ):

        # ----------------------------------------------------
        # 5M historical slice
        # ----------------------------------------------------

        current_5m = (
            df_5m_closed
            .iloc[: i + 1]
            .copy()
        )

        point_time = current_5m.iloc[-1][
            "open_time"
        ]

        # ----------------------------------------------------
        # 5M analysis
        # ----------------------------------------------------

        analysis_5m = analyze_5m(
            current_5m
        )

        if not analysis_5m:
            continue

        direction_5m = analysis_5m.get(
            "direction",
            "NEUTRAL",
        )

        sweep = analysis_5m.get(
            "liquidity_sweep",
            "NONE",
        )

        # ----------------------------------------------------
        # Historical HTF V3.1
        # ----------------------------------------------------

        htf_context = (
            build_historical_htf_context(
                df_1d_closed,
                df_4h_closed,
                df_1h_closed,
                df_15m_closed,
                point_time,
            )
        )

        if htf_context is None:
            continue

        v31_signal = htf_context.get(
            "signal",
            "WAIT",
        )

        # ----------------------------------------------------
        # Diagnostics
        # ----------------------------------------------------

        v31_wait_reason = (
            diagnose_v31_wait(
                htf_context
            )
        )

        rejection = (
            diagnose_sweep_rejection(
                sweep=sweep,
                v31_context=htf_context,
                direction_5m=direction_5m,
            )
        )

        # ----------------------------------------------------
        # Store result
        # ----------------------------------------------------

        result = {
            "time": str(point_time),

            "sweep": sweep,

            "v31_signal": v31_signal,

            "v31_confidence": htf_context.get(
                "confidence",
                0,
            ),

            "confirmations": htf_context.get(
                "confirmations",
                0,
            ),

            "1d": htf_context.get(
                "major_direction",
                "NEUTRAL",
            ),

            "4h": htf_context.get(
                "structure_direction",
                "NEUTRAL",
            ),

            "1h": htf_context.get(
                "h1_direction",
                "NEUTRAL",
            ),

            "15m": htf_context.get(
                "m15_direction",
                "NEUTRAL",
            ),

            "5m": direction_5m,

            "htf_agreement": htf_context.get(
                "htf_agreement",
                "MIXED",
            ),

            "market_phase": htf_context.get(
                "market_phase",
                "NONE",
            ),

            "entry_trigger": htf_context.get(
                "entry_trigger",
                "NO_TRIGGER",
            ),

            "v31_wait_reason": v31_wait_reason,

            "rejection": rejection,
        }

        results.append(
            result
        )

        # ----------------------------------------------------
        # Only store actual sweeps
        # ----------------------------------------------------

        if sweep != "NONE":

            sweep_diagnostics.append(
                result.copy()
            )

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        if len(results) % 25 == 0:

            print(
                f"Processed historical points: "
                f"{len(results)}"
            )

    # ========================================================
    # COMPLETE
    # ========================================================

    print()
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)

    print()
    print(
        f"Historical points: {len(results)}"
    )

    # ========================================================
    # LIQUIDITY SWEEP SUMMARY
    # ========================================================

    sweep_counter = Counter(
        r["sweep"]
        for r in results
        if r["sweep"] != "NONE"
    )

    bullish_sweeps = sweep_counter.get(
        "BULLISH_SWEEP",
        0,
    )

    bearish_sweeps = sweep_counter.get(
        "BEARISH_SWEEP",
        0,
    )

    total_sweeps = (
        bullish_sweeps
        + bearish_sweeps
    )

    aligned_sweeps = sum(
        1
        for r in sweep_diagnostics
        if r["rejection"]
        in (
            "READY_FOR_BUY",
            "READY_FOR_SELL",
        )
    )

    print()
    print(
        "LIQUIDITY SWEEP SUMMARY"
    )

    print(
        f"  Total sweeps: {total_sweeps}"
    )

    print(
        f"  Bullish sweeps: {bullish_sweeps}"
    )

    print(
        f"  Bearish sweeps: {bearish_sweeps}"
    )

    print(
        f"  V3.1 + sweep aligned: "
        f"{aligned_sweeps}"
    )

    # ========================================================
    # V3.1 DISTRIBUTION
    # ========================================================

    v31_counter = Counter(
        r["v31_signal"]
        for r in results
    )

    print()
    print(
        "V3.1 SIGNAL DISTRIBUTION"
    )

    for signal in (
        "BUY",
        "SELL",
        "WAIT",
    ):

        print(
            f"  {signal:<15}"
            f"{v31_counter.get(signal, 0)}"
        )

    # ========================================================
    # FINAL STRATEGY DISTRIBUTION
    # ========================================================

    final_counter = Counter()

    for r in results:

        if r["sweep"] == "NONE":

            final_signal = "NO_TRADE"

        elif r["rejection"] == "READY_FOR_BUY":

            final_signal = "BUY"

        elif r["rejection"] == "READY_FOR_SELL":

            final_signal = "SELL"

        else:

            final_signal = "NO_TRADE"

        final_counter[
            final_signal
        ] += 1

    print()
    print(
        "FINAL STRATEGY SIGNAL DISTRIBUTION"
    )

    for signal in (
        "BUY",
        "SELL",
        "NO_TRADE",
    ):

        print(
            f"  {signal:<15}"
            f"{final_counter.get(signal, 0)}"
        )

    # ========================================================
    # DIRECTION DISTRIBUTION
    # ========================================================

    print()
    print(
        "DIRECTION DISTRIBUTION"
    )

    for field, label in (
        ("1d", "1D"),
        ("4h", "4H"),
        ("1h", "1H"),
        ("15m", "15M"),
        ("5m", "5M"),
    ):

        counter = Counter(
            r[field]
            for r in results
        )

        print()
        print(
            f"{label}:"
        )

        for direction in (
            "BULLISH",
            "BEARISH",
            "NEUTRAL",
        ):

            count = counter.get(
                direction,
                0,
            )

            if count:

                print(
                    f"  {direction:<20}"
                    f"{count}"
                )

    # ========================================================
    # SWEEP REJECTION REASONS
    # ========================================================

    rejection_counter = Counter(
        r["rejection"]
        for r in sweep_diagnostics
    )

    print()
    print("=" * 70)
    print(
        "SWEEP REJECTION REASONS"
    )
    print("=" * 70)

    if rejection_counter:

        for reason, count in (
            rejection_counter.most_common()
        ):

            print(
                f"  {reason:<35}"
                f"{count}"
            )

    else:

        print(
            "  No sweep rejection data."
        )

    # ========================================================
    # V3.1 WAIT REASONS
    # ========================================================

    wait_reason_counter = Counter(
        r["v31_wait_reason"]
        for r in sweep_diagnostics
        if r["v31_signal"] == "WAIT"
    )

    print()
    print("=" * 70)
    print(
        "V3.1 WAIT REASONS ON SWEEP POINTS"
    )
    print("=" * 70)

    if wait_reason_counter:

        for reason, count in (
            wait_reason_counter.most_common()
        ):

            print(
                f"  {reason:<35}"
                f"{count}"
            )

    else:

        print(
            "  No V3.1 WAIT data."
        )

    # ========================================================
    # SWEEP vs 5M
    # ========================================================

    sweep_5m_counter = Counter()

    for r in sweep_diagnostics:

        key = (
            r["sweep"],
            r["5m"],
        )

        sweep_5m_counter[
            key
        ] += 1

    print()
    print("=" * 70)
    print(
        "SWEEP vs 5M DIRECTION"
    )
    print("=" * 70)

    if sweep_5m_counter:

        for (
            sweep,
            direction,
        ), count in sorted(
            sweep_5m_counter.items()
        ):

            print(
                f"  {sweep:<20}"
                f" + {direction:<10}"
                f": {count}"
            )

    else:

        print(
            "  No sweep data."
        )

    # ========================================================
    # HTF PATTERNS
    # ========================================================

    htf_pattern_counter = Counter()

    for r in sweep_diagnostics:

        key = (
            r["1d"],
            r["4h"],
            r["1h"],
            r["15m"],
        )

        htf_pattern_counter[
            key
        ] += 1

    print()
    print("=" * 70)
    print(
        "HTF DIRECTION PATTERNS ON SWEEP POINTS"
    )
    print("=" * 70)

    if htf_pattern_counter:

        for pattern, count in (
            htf_pattern_counter.most_common()
        ):

            print(
                f"  "
                f"1D={pattern[0]:<8} "
                f"4H={pattern[1]:<8} "
                f"1H={pattern[2]:<8} "
                f"15M={pattern[3]:<8} "
                f": {count}"
            )

    else:

        print(
            "  No HTF pattern data."
        )

    # ========================================================
    # DETAILED SWEEP TABLE
    # ========================================================

    if PRINT_SWEEP_DETAILS:

        print_sweep_diagnostic(
            sweep_diagnostics
        )

    # ========================================================
    # FINAL NOTES
    # ========================================================

    print()
    print("=" * 70)
    print("IMPORTANT")
    print("=" * 70)

    print(
        "This run is diagnostic only."
    )

    print(
        "The original "
        "analysis/signal_engine.py "
        "was NOT modified."
    )

    print(
        "Historical analysis uses closed candles "
        "only."
    )

    print(
        "The current-data HTF adapter is NOT used "
        "during historical testing."
    )

    print()
    print(
        "No strategy parameters were changed."
    )

    print()
    print(
        f"Analysis finished: {utc_now()}"
    )

    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()