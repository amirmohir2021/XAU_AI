import sys
from pathlib import Path
import math

# ---------------------------------------------------------
# PROJECT ROOT
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------

from data.market_data import get_xauusd_candles
from analysis.indicators import (
    calculate_indicators,
    get_latest_indicator_values,
)
from analysis.structure import analyze_structure


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

TIMEFRAMES = ["1d", "4h", "1h", "15m"]

CANDLE_LIMIT = 300


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def safe_float(value):
    try:
        if value is None:
            return None

        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------
# TREND
# ---------------------------------------------------------

def determine_trend(indicators):
    close = safe_float(indicators.get("close"))
    ema20 = safe_float(indicators.get("EMA20"))
    ema50 = safe_float(indicators.get("EMA50"))
    ema200 = safe_float(indicators.get("EMA200"))

    if close is None:
        return "NEUTRAL"

    if ema20 is not None and ema50 is not None and ema200 is not None:

        if close > ema20 > ema50 > ema200:
            return "BULLISH"

        if close < ema20 < ema50 < ema200:
            return "BEARISH"

    if ema20 is not None and ema50 is not None:

        if close > ema20 and ema20 > ema50:
            return "BULLISH"

        if close < ema20 and ema20 < ema50:
            return "BEARISH"

    return "NEUTRAL"


# ---------------------------------------------------------
# MOMENTUM
# ---------------------------------------------------------

def determine_momentum(indicators):
    rsi = safe_float(indicators.get("RSI14"))
    macd_hist = safe_float(indicators.get("MACD_HIST"))
    stoch_k = safe_float(indicators.get("STOCH_K"))
    stoch_d = safe_float(indicators.get("STOCH_D"))

    bullish_score = 0
    bearish_score = 0

    # RSI
    if rsi is not None:

        if rsi > 55:
            bullish_score += 1

        elif rsi < 45:
            bearish_score += 1

    # MACD
    if macd_hist is not None:

        if macd_hist > 0:
            bullish_score += 1

        elif macd_hist < 0:
            bearish_score += 1

    # Stochastic
    if stoch_k is not None and stoch_d is not None:

        if stoch_k > stoch_d:
            bullish_score += 1

        elif stoch_k < stoch_d:
            bearish_score += 1

    if bullish_score > bearish_score:
        return "BULLISH"

    if bearish_score > bullish_score:
        return "BEARISH"

    return "NEUTRAL"


# ---------------------------------------------------------
# MARKET STRENGTH
# ---------------------------------------------------------

def determine_strength(indicators):
    adx = safe_float(indicators.get("ADX14"))

    if adx is None:
        return "UNKNOWN"

    if adx >= 25:
        return "STRONG"

    if adx >= 20:
        return "MODERATE"

    return "WEAK"


# ---------------------------------------------------------
# STRUCTURE SUMMARY
# ---------------------------------------------------------

def extract_structure_summary(structure):
    if not structure:
        return {
            "trend": "NEUTRAL",
            "points": [],
            "bos": [],
            "choch": [],
            "support": [],
            "resistance": [],
        }

    # Yangi structure.py format
    structure_points = structure.get("points", [])

    # Eski formatlar uchun fallback
    if not structure_points:
        structure_points = structure.get(
            "structure_points",
            structure.get("swings", [])
        )

    bos = structure.get(
        "bos",
        structure.get("BOS", [])
    )

    choch = structure.get(
        "choch",
        structure.get("CHOCH", [])
    )

    supports = structure.get(
        "support",
        structure.get("supports", [])
    )

    resistances = structure.get(
        "resistance",
        structure.get("resistances", [])
    )

    trend = structure.get(
        "trend",
        structure.get("structure_trend", "NEUTRAL")
    )

    return {
        "trend": trend,
        "points": structure_points,
        "bos": bos,
        "choch": choch,
        "support": supports,
        "resistance": resistances,
    }


# ---------------------------------------------------------
# TIMEFRAME ANALYSIS
# ---------------------------------------------------------

def analyze_timeframe(timeframe):
    print()
    print("=" * 70)
    print(f"TIMEFRAME: {timeframe}")
    print("=" * 70)

    # -----------------------------------------------------
    # DATA
    # -----------------------------------------------------

    df = get_xauusd_candles(
        interval=timeframe,
        limit=CANDLE_LIMIT
    )

    if df is None or df.empty:
        print("No market data.")
        return None

    print(f"Candles: {len(df)}")

    # -----------------------------------------------------
    # INDICATORS
    # -----------------------------------------------------

    df = calculate_indicators(df)

    indicators = get_latest_indicator_values(df)

    trend = determine_trend(indicators)
    momentum = determine_momentum(indicators)
    strength = determine_strength(indicators)

    # -----------------------------------------------------
    # PRICE
    # -----------------------------------------------------

    close = safe_float(indicators.get("close"))

    print()
    print("PRICE")
    print("-" * 40)

    if close is not None:
        print(f"Close           : {close:.3f}")

    # -----------------------------------------------------
    # INDICATORS
    # -----------------------------------------------------

    print()
    print("INDICATORS")
    print("-" * 40)

    for key, value in indicators.items():

        if key == "close":
            continue

        value = safe_float(value)

        if value is not None:
            print(f"{key:<16}: {value:.4f}")

    # -----------------------------------------------------
    # BASIC ANALYSIS
    # -----------------------------------------------------

    print()
    print("BASIC ANALYSIS")
    print("-" * 40)

    print(f"Trend           : {trend}")
    print(f"Momentum        : {momentum}")
    print(f"Strength        : {strength}")

    # -----------------------------------------------------
    # STRUCTURE
    # -----------------------------------------------------

    structure_summary = {
        "trend": "NEUTRAL",
        "points": [],
        "bos": [],
        "choch": [],
        "support": [],
        "resistance": [],
    }

    # Hozircha market structure faqat 4H da
    if timeframe == "4h":

        structure = analyze_structure(df)

        structure_summary = extract_structure_summary(
            structure
        )

        print()
        print("MARKET STRUCTURE")
        print("-" * 40)

        print(
            f"Structure trend : "
            f"{structure_summary['trend']}"
        )

        print(
            f"Structure points: "
            f"{len(structure_summary['points'])}"
        )

        print(
            f"BOS             : "
            f"{len(structure_summary['bos'])}"
        )

        print(
            f"CHOCH           : "
            f"{len(structure_summary['choch'])}"
        )

        print(
            f"Supports        : "
            f"{len(structure_summary['support'])}"
        )

        print(
            f"Resistances     : "
            f"{len(structure_summary['resistance'])}"
        )

        # -------------------------------------------------
        # LAST STRUCTURE POINTS
        # -------------------------------------------------

        points = structure_summary["points"]

        if points:

            print()
            print("LAST STRUCTURE POINTS")
            print("-" * 70)

            for point in points[-8:]:

                index = point.get(
                    "index",
                    "?"
                )

                point_type = point.get(
                    "type",
                    "?"
                )

                label = point.get(
                    "label",
                    "?"
                )

                price = safe_float(
                    point.get("price")
                )

                if price is not None:

                    print(
                        f"{index:>4} | "
                        f"{point_type:<5} | "
                        f"{label:<4} | "
                        f"{price:.3f}"
                    )

        # -------------------------------------------------
        # SUPPORT
        # -------------------------------------------------

        supports = structure_summary["support"]

        if supports:

            print()
            print("SUPPORT")
            print("-" * 70)

            for level in supports:

                center = safe_float(
                    level.get("price")
                )

                low = safe_float(
                    level.get("low")
                )

                high = safe_float(
                    level.get("high")
                )

                touches = level.get(
                    "touches",
                    0
                )

                if center is None:
                    continue

                if low is not None and high is not None:

                    print(
                        f"{center:.3f} | "
                        f"zone: {low:.3f} - {high:.3f} | "
                        f"touches={touches}"
                    )

                else:

                    print(
                        f"{center:.3f} | "
                        f"touches={touches}"
                    )

        # -------------------------------------------------
        # RESISTANCE
        # -------------------------------------------------

        resistances = structure_summary["resistance"]

        if resistances:

            print()
            print("RESISTANCE")
            print("-" * 70)

            for level in resistances:

                center = safe_float(
                    level.get("price")
                )

                low = safe_float(
                    level.get("low")
                )

                high = safe_float(
                    level.get("high")
                )

                touches = level.get(
                    "touches",
                    0
                )

                if center is None:
                    continue

                if low is not None and high is not None:

                    print(
                        f"{center:.3f} | "
                        f"zone: {low:.3f} - {high:.3f} | "
                        f"touches={touches}"
                    )

                else:

                    print(
                        f"{center:.3f} | "
                        f"touches={touches}"
                    )

        # -------------------------------------------------
        # RECENT BOS
        # -------------------------------------------------

        bos = structure_summary["bos"]

        if bos:

            print()
            print("RECENT BOS")
            print("-" * 70)

            for event in bos[-5:]:

                print(event)

        # -------------------------------------------------
        # RECENT CHOCH
        # -------------------------------------------------

        choch = structure_summary["choch"]

        if choch:

            print()
            print("RECENT CHOCH")
            print("-" * 70)

            for event in choch[-5:]:

                print(event)

    # -----------------------------------------------------
    # RETURN
    # -----------------------------------------------------

    return {
        "timeframe": timeframe,
        "indicators": indicators,
        "trend": trend,
        "momentum": momentum,
        "strength": strength,
        "structure": structure_summary,
    }


# ---------------------------------------------------------
# MULTI TIMEFRAME SUMMARY
# ---------------------------------------------------------

def build_mtf_summary(results):

    bullish_score = 0
    bearish_score = 0

    weights = {
        "1d": 4,
        "4h": 3,
        "1h": 2,
        "15m": 1,
    }

    for timeframe, result in results.items():

        if result is None:
            continue

        weight = weights.get(
            timeframe,
            1
        )

        trend = result.get(
            "trend",
            "NEUTRAL"
        )

        momentum = result.get(
            "momentum",
            "NEUTRAL"
        )

        # Trend
        if trend == "BULLISH":
            bullish_score += 2 * weight

        elif trend == "BEARISH":
            bearish_score += 2 * weight

        # Momentum
        if momentum == "BULLISH":
            bullish_score += weight

        elif momentum == "BEARISH":
            bearish_score += weight

    total = bullish_score + bearish_score

    if bullish_score > bearish_score:
        direction = "BULLISH"

    elif bearish_score > bullish_score:
        direction = "BEARISH"

    else:
        direction = "NEUTRAL"

    if total > 0:
        balance_score = (
            abs(bullish_score - bearish_score)
            / total
            * 100
        )
    else:
        balance_score = 0

    return {
        "direction": direction,
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
        "balance_score": balance_score,
    }


# ---------------------------------------------------------
# REPORT
# ---------------------------------------------------------

def print_mtf_report(summary):

    print()
    print()
    print("#" * 70)
    print("XAU/USD MULTI-TIMEFRAME ANALYSIS")
    print("#" * 70)

    print()
    print("MULTI-TIMEFRAME SUMMARY")
    print("-" * 40)

    print(
        f"Direction       : "
        f"{summary['direction']}"
    )

    print(
        f"Bullish score   : "
        f"{summary['bullish_score']}"
    )

    print(
        f"Bearish score   : "
        f"{summary['bearish_score']}"
    )

    print(
        f"Balance score   : "
        f"{summary['balance_score']:.2f}%"
    )

    print()
    print(
        "NOTE: Balance score is an internal "
        "technical score, not a probability."
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print()
    print("#" * 70)
    print("XAU/USD ANALYZER")
    print("#" * 70)

    results = {}

    for timeframe in TIMEFRAMES:

        try:

            result = analyze_timeframe(
                timeframe
            )

            results[timeframe] = result

        except Exception as error:

            print()
            print(
                f"[ERROR] {timeframe}: "
                f"{type(error).__name__}: {error}"
            )

            results[timeframe] = None

    # -----------------------------------------------------
    # MTF
    # -----------------------------------------------------

    summary = build_mtf_summary(
        results
    )

    print_mtf_report(
        summary
    )

    print()
    print("#" * 70)
    print("ANALYSIS FINISHED")
    print("#" * 70)
    print()


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------

if __name__ == "__main__":
    main()