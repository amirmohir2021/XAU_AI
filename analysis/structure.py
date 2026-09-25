import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pandas as pd
import numpy as np


# =========================================================
# SETTINGS
# =========================================================

SWING_LEFT = 3
SWING_RIGHT = 3

ATR_PERIOD = 14

# Breakout must exceed the level by this fraction of ATR.
# Example:
# ATR = 30
# ATR_BREAK_MULTIPLIER = 0.10
# minimum break distance = 3 points
ATR_BREAK_MULTIPLIER = 0.10

# Maximum number of support/resistance levels
MAX_LEVELS = 3

# Price clustering tolerance
LEVEL_TOLERANCE = 0.003


# =========================================================
# ATR
# =========================================================

def calculate_atr(df, period=ATR_PERIOD):

    high = df["high"]
    low = df["low"]
    close = df["close"]

    previous_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - previous_close).abs()
    tr3 = (low - previous_close).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    atr = true_range.rolling(
        period
    ).mean()

    return atr


# =========================================================
# SWING DETECTION
# =========================================================

def detect_swings(
    df,
    left=SWING_LEFT,
    right=SWING_RIGHT
):
    """
    Detect confirmed swing highs and swing lows.

    A candle becomes a swing only after 'right'
    candles have formed after it.

    This prevents using future information as if it
    were already known at the swing candle itself.
    """

    data = df.copy()

    data["swing_high"] = False
    data["swing_low"] = False

    data["swing_confirmation_index"] = np.nan

    highs = data["high"].values
    lows = data["low"].values

    length = len(data)

    for i in range(left, length - right):

        current_high = highs[i]
        current_low = lows[i]

        left_highs = highs[i - left:i]
        right_highs = highs[i + 1:i + right + 1]

        left_lows = lows[i - left:i]
        right_lows = lows[i + 1:i + right + 1]

        is_swing_high = (
            current_high > left_highs.max()
            and
            current_high >= right_highs.max()
        )

        is_swing_low = (
            current_low < left_lows.min()
            and
            current_low <= right_lows.min()
        )

        # -------------------------------------------------
        # A candle should not be both HIGH and LOW.
        # -------------------------------------------------

        if is_swing_high and is_swing_low:

            high_strength = (
                current_high
                - max(left_highs.max(), right_highs.max())
            )

            low_strength = (
                min(left_lows.min(), right_lows.min())
                - current_low
            )

            if high_strength >= low_strength:
                is_swing_low = False
            else:
                is_swing_high = False

        if is_swing_high:
            data.iloc[
                i,
                data.columns.get_loc("swing_high")
            ] = True

            data.iloc[
                i,
                data.columns.get_loc(
                    "swing_confirmation_index"
                )
            ] = i + right

        if is_swing_low:
            data.iloc[
                i,
                data.columns.get_loc("swing_low")
            ] = True

            data.iloc[
                i,
                data.columns.get_loc(
                    "swing_confirmation_index"
                )
            ] = i + right

    return data


# =========================================================
# GET SWING POINTS
# =========================================================

def get_swing_points(df):

    points = []

    for index, row in df.iterrows():

        if bool(row.get("swing_high", False)):

            points.append({
                "index": index,
                "type": "HIGH",
                "price": float(row["high"]),
                "confirmation_index": int(
                    row["swing_confirmation_index"]
                )
                if not pd.isna(
                    row["swing_confirmation_index"]
                )
                else index,
            })

        if bool(row.get("swing_low", False)):

            points.append({
                "index": index,
                "type": "LOW",
                "price": float(row["low"]),
                "confirmation_index": int(
                    row["swing_confirmation_index"]
                )
                if not pd.isna(
                    row["swing_confirmation_index"]
                )
                else index,
            })

    points.sort(
        key=lambda x: x["index"]
    )

    return points


# =========================================================
# CLASSIFY MARKET STRUCTURE
# =========================================================

def classify_market_structure(points):

    classified = []

    last_high = None
    last_low = None

    for point in points:

        current = point.copy()

        point_type = current["type"]
        price = current["price"]

        # -------------------------------------------------
        # HIGH
        # -------------------------------------------------

        if point_type == "HIGH":

            if last_high is None:

                current["label"] = "FIRST_HIGH"

            elif price > last_high:

                current["label"] = "HH"

            else:

                current["label"] = "LH"

            last_high = price

        # -------------------------------------------------
        # LOW
        # -------------------------------------------------

        elif point_type == "LOW":

            if last_low is None:

                current["label"] = "FIRST_LOW"

            elif price > last_low:

                current["label"] = "HL"

            else:

                current["label"] = "LL"

            last_low = price

        classified.append(current)

    return classified


# =========================================================
# MARKET STRUCTURE TREND
# =========================================================

def determine_structure_trend(
    points,
    lookback=12
):

    if not points:
        return "NEUTRAL"

    recent = points[-lookback:]

    bullish = 0
    bearish = 0

    for point in recent:

        label = point.get(
            "label",
            ""
        )

        if label in ("HH", "HL"):
            bullish += 1

        elif label in ("LH", "LL"):
            bearish += 1

    if bullish > bearish:
        return "BULLISH"

    if bearish > bullish:
        return "BEARISH"

    return "NEUTRAL"


# =========================================================
# INITIAL STRUCTURE TREND
# =========================================================

def get_initial_trend(points):

    if len(points) < 3:
        return "NEUTRAL"

    bullish = 0
    bearish = 0

    for point in points[:8]:

        label = point.get(
            "label",
            ""
        )

        if label in ("HH", "HL"):
            bullish += 1

        elif label in ("LH", "LL"):
            bearish += 1

    if bullish > bearish:
        return "BULLISH"

    if bearish > bullish:
        return "BEARISH"

    return "NEUTRAL"


# =========================================================
# BREAK VALIDATION
# =========================================================

def is_valid_bullish_break(
    close_price,
    broken_level,
    atr_value
):

    if close_price is None:
        return False

    distance = close_price - broken_level

    if distance <= 0:
        return False

    if atr_value is None or atr_value <= 0:
        return True

    minimum_distance = (
        atr_value * ATR_BREAK_MULTIPLIER
    )

    return distance >= minimum_distance


def is_valid_bearish_break(
    close_price,
    broken_level,
    atr_value
):

    if close_price is None:
        return False

    distance = broken_level - close_price

    if distance <= 0:
        return False

    if atr_value is None or atr_value <= 0:
        return True

    minimum_distance = (
        atr_value * ATR_BREAK_MULTIPLIER
    )

    return distance >= minimum_distance


# =========================================================
# STRUCTURE EVENTS
# =========================================================

def detect_structure_events(
    df,
    structure_points
):

    if not structure_points:
        return [], []

    data = df.copy()

    if "ATR" not in data.columns:
        data["ATR"] = calculate_atr(data)

    bos = []
    choch = []

    current_trend = get_initial_trend(
        structure_points
    )

    broken_levels = set()

    # -----------------------------------------------------
    # Only confirmed structure points
    # -----------------------------------------------------

    for point in structure_points:

        point_index = point["index"]

        confirmation_index = point.get(
            "confirmation_index",
            point_index
        )

        # We start checking breaks only after
        # the structure point itself is confirmed.
        start_index = max(
            int(confirmation_index),
            int(point_index) + 1
        )

        broken_level = float(
            point["price"]
        )

        point_type = point["type"]

        if start_index >= len(data):
            continue

        # -------------------------------------------------
        # HIGH BREAK
        # -------------------------------------------------

        if point_type == "HIGH":

            for i in range(
                start_index,
                len(data)
            ):

                row = data.iloc[i]

                close_price = float(
                    row["close"]
                )

                high_price = float(
                    row["high"]
                )

                atr_value = (
                    float(row["ATR"])
                    if not pd.isna(row["ATR"])
                    else None
                )

                # -----------------------------------------
                # Bullish break requires CLOSE above level.
                # Wick alone is not enough.
                # -----------------------------------------

                if is_valid_bullish_break(
                    close_price,
                    broken_level,
                    atr_value
                ):

                    event_key = (
                        point_index,
                        "HIGH",
                        i
                    )

                    if event_key in broken_levels:
                        break

                    broken_levels.add(
                        event_key
                    )

                    event = {
                        "index": i,
                        "time": (
                            data.index[i]
                            if hasattr(
                                data.index,
                                "dtype"
                            )
                            else i
                        ),
                        "type": "BULLISH_BOS",
                        "price": close_price,
                        "broken_level": broken_level,
                        "atr": atr_value,
                        "confirmation": "CLOSE",
                    }

                    # -------------------------------------
                    # If previous structure was bearish,
                    # this is CHOCH.
                    # Otherwise BOS.
                    # -------------------------------------

                    if current_trend == "BEARISH":

                        event["type"] = (
                            "BULLISH_CHOCH"
                        )

                        choch.append(event)

                        current_trend = "BULLISH"

                    else:

                        bos.append(event)

                    break

        # -------------------------------------------------
        # LOW BREAK
        # -------------------------------------------------

        elif point_type == "LOW":

            for i in range(
                start_index,
                len(data)
            ):

                row = data.iloc[i]

                close_price = float(
                    row["close"]
                )

                low_price = float(
                    row["low"]
                )

                atr_value = (
                    float(row["ATR"])
                    if not pd.isna(row["ATR"])
                    else None
                )

                # -----------------------------------------
                # Bearish break requires CLOSE below level.
                # Wick alone is not enough.
                # -----------------------------------------

                if is_valid_bearish_break(
                    close_price,
                    broken_level,
                    atr_value
                ):

                    event_key = (
                        point_index,
                        "LOW",
                        i
                    )

                    if event_key in broken_levels:
                        break

                    broken_levels.add(
                        event_key
                    )

                    event = {
                        "index": i,
                        "time": (
                            data.index[i]
                            if hasattr(
                                data.index,
                                "dtype"
                            )
                            else i
                        ),
                        "type": "BEARISH_BOS",
                        "price": close_price,
                        "broken_level": broken_level,
                        "atr": atr_value,
                        "confirmation": "CLOSE",
                    }

                    # -------------------------------------
                    # If previous structure was bullish,
                    # this is CHOCH.
                    # -------------------------------------

                    if current_trend == "BULLISH":

                        event["type"] = (
                            "BEARISH_CHOCH"
                        )

                        choch.append(event)

                        current_trend = "BEARISH"

                    else:

                        bos.append(event)

                    break

    return bos, choch


# =========================================================
# BOS
# =========================================================

def detect_bos(
    df,
    structure_points
):

    bos, _ = detect_structure_events(
        df,
        structure_points
    )

    return bos


# =========================================================
# CHOCH
# =========================================================

def detect_choch(
    df,
    structure_points
):

    _, choch = detect_structure_events(
        df,
        structure_points
    )

    return choch


# =========================================================
# LEVEL CLUSTERING
# =========================================================

def _cluster_levels(
    levels,
    tolerance=LEVEL_TOLERANCE
):

    if not levels:
        return []

    sorted_levels = sorted(
        levels,
        key=lambda x: x["price"]
    )

    clusters = []

    for level in sorted_levels:

        price = level["price"]

        if not clusters:

            clusters.append(
                [level]
            )

            continue

        cluster = clusters[-1]

        cluster_prices = [
            item["price"]
            for item in cluster
        ]

        center = sum(
            cluster_prices
        ) / len(cluster_prices)

        if center == 0:

            cluster.append(level)

        elif abs(price - center) / center <= tolerance:

            cluster.append(level)

        else:

            clusters.append(
                [level]
            )

    return clusters


# =========================================================
# SUPPORT / RESISTANCE
# =========================================================

def find_support_resistance(
    df,
    structure_points,
    tolerance=LEVEL_TOLERANCE,
    max_levels=MAX_LEVELS
):

    if not structure_points:
        return [], []

    current_price = float(
        df["close"].iloc[-1]
    )

    supports_raw = []
    resistances_raw = []

    # -----------------------------------------------------
    # Use confirmed structural lows/highs only.
    # -----------------------------------------------------

    for point in structure_points:

        price = float(
            point["price"]
        )

        item = {
            "price": price,
            "index": point["index"],
            "label": point.get(
                "label",
                ""
            ),
            "type": point["type"],
        }

        if point["type"] == "LOW":

            if price <= current_price:

                supports_raw.append(item)

        elif point["type"] == "HIGH":

            if price >= current_price:

                resistances_raw.append(item)

    # -----------------------------------------------------
    # Cluster supports
    # -----------------------------------------------------

    support_clusters = _cluster_levels(
        supports_raw,
        tolerance
    )

    resistance_clusters = _cluster_levels(
        resistances_raw,
        tolerance
    )

    supports = []

    for cluster in support_clusters:

        prices = [
            item["price"]
            for item in cluster
        ]

        center = sum(prices) / len(prices)

        supports.append({
            "price": center,
            "low": min(prices),
            "high": max(prices),
            "touches": len(cluster),
            "strength": len(cluster),
        })

    resistances = []

    for cluster in resistance_clusters:

        prices = [
            item["price"]
            for item in cluster
        ]

        center = sum(prices) / len(prices)

        resistances.append({
            "price": center,
            "low": min(prices),
            "high": max(prices),
            "touches": len(cluster),
            "strength": len(cluster),
        })

    # -----------------------------------------------------
    # Nearest levels first
    # -----------------------------------------------------

    supports.sort(
        key=lambda x: abs(
            current_price - x["price"]
        )
    )

    resistances.sort(
        key=lambda x: abs(
            current_price - x["price"]
        )
    )

    supports = supports[
        :max_levels
    ]

    resistances = resistances[
        :max_levels
    ]

    return supports, resistances


# =========================================================
# FALSE BREAKOUT DETECTION
# =========================================================

def detect_false_breakouts(
    df,
    structure_points
):

    if not structure_points:
        return []

    data = df.copy()

    if "ATR" not in data.columns:
        data["ATR"] = calculate_atr(data)

    events = []

    # -----------------------------------------------------
    # Check structural levels
    # -----------------------------------------------------

    for point in structure_points:

        level = float(
            point["price"]
        )

        point_index = int(
            point["index"]
        )

        point_type = point["type"]

        start_index = max(
            point_index + 1,
            int(
                point.get(
                    "confirmation_index",
                    point_index
                )
            )
        )

        for i in range(
            start_index,
            len(data)
        ):

            row = data.iloc[i]

            close_price = float(
                row["close"]
            )

            high_price = float(
                row["high"]
            )

            low_price = float(
                row["low"]
            )

            atr_value = (
                float(row["ATR"])
                if not pd.isna(row["ATR"])
                else None
            )

            # -------------------------------------------------
            # HIGH false breakout
            #
            # Price goes above level intrabar,
            # but closes back below it.
            # -------------------------------------------------

            if point_type == "HIGH":

                if high_price > level:

                    if close_price < level:

                        wick_distance = (
                            high_price - level
                        )

                        if (
                            atr_value is None
                            or wick_distance
                            >= atr_value * 0.05
                        ):

                            events.append({
                                "index": i,
                                "type": (
                                    "FALSE_BULLISH_BREAK"
                                ),
                                "level": level,
                                "high": high_price,
                                "close": close_price,
                                "atr": atr_value,
                            })

                            break

            # -------------------------------------------------
            # LOW false breakout
            #
            # Price goes below level intrabar,
            # but closes back above it.
            # -------------------------------------------------

            elif point_type == "LOW":

                if low_price < level:

                    if close_price > level:

                        wick_distance = (
                            level - low_price
                        )

                        if (
                            atr_value is None
                            or wick_distance
                            >= atr_value * 0.05
                        ):

                            events.append({
                                "index": i,
                                "type": (
                                    "FALSE_BEARISH_BREAK"
                                ),
                                "level": level,
                                "low": low_price,
                                "close": close_price,
                                "atr": atr_value,
                            })

                            break

    return events


# =========================================================
# MAIN STRUCTURE ANALYSIS
# =========================================================

def analyze_structure(df):

    if df is None or df.empty:

        return {
            "trend": "NEUTRAL",
            "points": [],
            "bos": [],
            "choch": [],
            "support": [],
            "resistance": [],
            "false_breakouts": [],
        }

    # -----------------------------------------------------
    # ATR
    # -----------------------------------------------------

    data = df.copy()

    if "ATR" not in data.columns:

        data["ATR"] = calculate_atr(
            data
        )

    # -----------------------------------------------------
    # Swings
    # -----------------------------------------------------

    data = detect_swings(
        data
    )

    # -----------------------------------------------------
    # Points
    # -----------------------------------------------------

    raw_points = get_swing_points(
        data
    )

    points = classify_market_structure(
        raw_points
    )

    # -----------------------------------------------------
    # Trend
    # -----------------------------------------------------

    trend = determine_structure_trend(
        points
    )

    # -----------------------------------------------------
    # BOS / CHOCH
    # -----------------------------------------------------

    bos, choch = detect_structure_events(
        data,
        points
    )

    # -----------------------------------------------------
    # Support / Resistance
    # -----------------------------------------------------

    support, resistance = (
        find_support_resistance(
            data,
            points
        )
    )

    # -----------------------------------------------------
    # False Breakouts
    # -----------------------------------------------------

    false_breakouts = (
        detect_false_breakouts(
            data,
            points
        )
    )

    # -----------------------------------------------------
    # Result
    # -----------------------------------------------------

    return {
        "trend": trend,
        "points": points,
        "bos": bos,
        "choch": choch,
        "support": support,
        "resistance": resistance,
        "false_breakouts": false_breakouts,
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    from data.market_data import (
        get_xauusd_candles
    )

    print()
    print("=" * 70)
    print("XAU/USD MARKET STRUCTURE TEST")
    print("=" * 70)

    df = get_xauusd_candles(
        interval="4h",
        limit=300
    )

    if df is None or df.empty:

        print("No market data.")

    else:

        result = analyze_structure(
            df
        )

        print()
        print(
            "Trend:",
            result["trend"]
        )

        print(
            "Structure points:",
            len(result["points"])
        )

        print(
            "BOS:",
            len(result["bos"])
        )

        print(
            "CHOCH:",
            len(result["choch"])
        )

        print(
            "False breakouts:",
            len(
                result["false_breakouts"]
            )
        )

        print()
        print("LAST STRUCTURE POINTS")
        print("-" * 70)

        for point in result["points"][-15:]:

            print(
                f"{point['index']:>4} | "
                f"{point['type']:<5} | "
                f"{point['label']:<10} | "
                f"{point['price']:.3f}"
            )

        print()
        print("RECENT BOS")
        print("-" * 70)

        for event in result["bos"][-5:]:

            print(event)

        print()
        print("RECENT CHOCH")
        print("-" * 70)

        for event in result["choch"][-5:]:

            print(event)

        print()
        print("FALSE BREAKOUTS")
        print("-" * 70)

        for event in result[
            "false_breakouts"
        ][-5:]:

            print(event)

        print()
        print("SUPPORT")
        print("-" * 70)

        for level in result["support"]:

            print(
                f"{level['price']:.3f} | "
                f"zone: "
                f"{level['low']:.3f} - "
                f"{level['high']:.3f} | "
                f"touches="
                f"{level['touches']}"
            )

        print()
        print("RESISTANCE")
        print("-" * 70)

        for level in result["resistance"]:

            print(
                f"{level['price']:.3f} | "
                f"zone: "
                f"{level['low']:.3f} - "
                f"{level['high']:.3f} | "
                f"touches="
                f"{level['touches']}"
            )

        print()
        print("=" * 70)
        print("TEST FINISHED")
        print("=" * 70)