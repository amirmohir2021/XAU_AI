
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd


# ============================================================
# SWING DETECTION
# ============================================================

def detect_swings(df, left=3, right=3):
    """
    Detect confirmed swing highs and swing lows.

    A swing is confirmed only after `right` candles have formed.
    """

    data = df.copy()

    data["swing_high"] = False
    data["swing_low"] = False
    data["swing_confirmation_index"] = None

    highs = data["high"].values
    lows = data["low"].values

    for i in range(left, len(data) - right):

        current_high = highs[i]
        current_low = lows[i]

        left_highs = highs[i - left:i]
        right_highs = highs[i + 1:i + right + 1]

        left_lows = lows[i - left:i]
        right_lows = lows[i + 1:i + right + 1]

        is_high = (
            current_high >= max(left_highs)
            and current_high >= max(right_highs)
        )

        is_low = (
            current_low <= min(left_lows)
            and current_low <= min(right_lows)
        )

        # Prevent one candle from becoming both HIGH and LOW.
        if is_high and is_low:

            high_strength = (
                current_high - max(left_highs)
            ) + (
                current_high - max(right_highs)
            )

            low_strength = (
                min(left_lows) - current_low
            ) + (
                min(right_lows) - current_low
            )

            if high_strength >= low_strength:
                is_low = False
            else:
                is_high = False

        confirmation_index = i + right

        if is_high:
            data.iloc[i, data.columns.get_loc("swing_high")] = True
            data.iloc[
                i,
                data.columns.get_loc("swing_confirmation_index")
            ] = confirmation_index

        elif is_low:
            data.iloc[i, data.columns.get_loc("swing_low")] = True
            data.iloc[
                i,
                data.columns.get_loc("swing_confirmation_index")
            ] = confirmation_index

    return data


# ============================================================
# STRUCTURE POINTS
# ============================================================

def get_swing_points(df):
    """
    Convert swing candles into structure points.
    """

    points = []

    for i, row in df.iterrows():

        if row.get("swing_high", False):

            points.append({
                "index": i,
                "time": row.name,
                "type": "HIGH",
                "price": float(row["high"]),
                "confirmation_index": row.get(
                    "swing_confirmation_index"
                ),
            })

        elif row.get("swing_low", False):

            points.append({
                "index": i,
                "time": row.name,
                "type": "LOW",
                "price": float(row["low"]),
                "confirmation_index": row.get(
                    "swing_confirmation_index"
                ),
            })

    return points


# ============================================================
# MARKET STRUCTURE CLASSIFICATION
# ============================================================

def classify_market_structure(points):
    """
    Classify structure points as:

    HIGH:
        HH = Higher High
        LH = Lower High

    LOW:
        HL = Higher Low
        LL = Lower Low
    """

    classified = []

    last_high = None
    last_low = None

    for point in points:

        item = point.copy()

        if point["type"] == "HIGH":

            if last_high is None:
                item["classification"] = "FIRST_HIGH"

            elif point["price"] > last_high:
                item["classification"] = "HH"

            else:
                item["classification"] = "LH"

            last_high = point["price"]

        else:

            if last_low is None:
                item["classification"] = "FIRST_LOW"

            elif point["price"] > last_low:
                item["classification"] = "HL"

            else:
                item["classification"] = "LL"

            last_low = point["price"]

        classified.append(item)

    return classified


# ============================================================
# STRUCTURE TREND
# ============================================================

def determine_structure_trend(points):
    """
    Determine trend from recent HH/HL/LH/LL structure.
    """

    if not points:
        return "UNKNOWN"

    recent = points[-12:]

    bullish = 0
    bearish = 0

    for point in recent:

        classification = point.get("classification")

        if classification in ("HH", "HL"):
            bullish += 1

        elif classification in ("LH", "LL"):
            bearish += 1

    if bullish > bearish:
        return "BULLISH"

    if bearish > bullish:
        return "BEARISH"

    return "RANGE"


# ============================================================
# INITIAL TREND
# ============================================================

def _get_initial_trend(points):
    """
    Determine the initial directional bias from structure.
    """

    if len(points) < 4:
        return "UNKNOWN"

    bullish = 0
    bearish = 0

    for point in points[-12:]:

        classification = point.get("classification")

        if classification in ("HH", "HL"):
            bullish += 1

        elif classification in ("LH", "LL"):
            bearish += 1

    if bullish > bearish:
        return "BULLISH"

    if bearish > bullish:
        return "BEARISH"

    return "RANGE"


# ============================================================
# BOS / CHOCH
# ============================================================

def detect_structure_events(df, structure_points):
    """
    Detect BOS and CHOCH.

    A structure point becomes breakable only after its
    confirmation candle has formed.
    """

    if not structure_points:
        return [], []

    bos_events = []
    choch_events = []

    initial_trend = _get_initial_trend(structure_points)

    broken_highs = set()
    broken_lows = set()

    current_trend = initial_trend

    for i in range(len(df)):

        row = df.iloc[i]

        close_price = float(row["close"])

        # ----------------------------------------------------
        # HIGH BREAKS
        # ----------------------------------------------------

        for point_id, point in enumerate(structure_points):

            if point_id in broken_highs:
                continue

            if point["type"] != "HIGH":
                continue

            confirmation_index = point.get("confirmation_index")

            if confirmation_index is None:
                continue

            if i <= confirmation_index:
                continue

            level = float(point["price"])

            if close_price > level:

                broken_highs.add(point_id)

                if current_trend == "BEARISH":

                    choch_events.append({
                        "index": i,
                        "time": row.name,
                        "type": "BULLISH_CHOCH",
                        "price": close_price,
                        "broken_level": level,
                    })

                    current_trend = "BULLISH"

                else:

                    bos_events.append({
                        "index": i,
                        "time": row.name,
                        "type": "BULLISH_BOS",
                        "price": close_price,
                        "broken_level": level,
                    })

        # ----------------------------------------------------
        # LOW BREAKS
        # ----------------------------------------------------

        for point_id, point in enumerate(structure_points):

            if point_id in broken_lows:
                continue

            if point["type"] != "LOW":
                continue

            confirmation_index = point.get("confirmation_index")

            if confirmation_index is None:
                continue

            if i <= confirmation_index:
                continue

            level = float(point["price"])

            if close_price < level:

                broken_lows.add(point_id)

                if current_trend == "BULLISH":

                    choch_events.append({
                        "index": i,
                        "time": row.name,
                        "type": "BEARISH_CHOCH",
                        "price": close_price,
                        "broken_level": level,
                    })

                    current_trend = "BEARISH"

                else:

                    bos_events.append({
                        "index": i,
                        "time": row.name,
                        "type": "BEARISH_BOS",
                        "price": close_price,
                        "broken_level": level,
                    })

    return bos_events, choch_events


def detect_bos(df, structure_points):
    bos_events, _ = detect_structure_events(
        df,
        structure_points
    )

    return bos_events


def detect_choch(df, structure_points):
    _, choch_events = detect_structure_events(
        df,
        structure_points
    )

    return choch_events


# ============================================================
# PRICE LEVEL CLUSTERING
# ============================================================

def _cluster_levels(levels, tolerance=0.003):
    """
    Group nearby price levels into zones.

    tolerance = percentage distance.
    Example:
        4280 and 4288 can become one zone.
    """

    if not levels:
        return []

    sorted_levels = sorted(levels)

    clusters = []
    current_cluster = [sorted_levels[0]]

    for price in sorted_levels[1:]:

        reference = sum(current_cluster) / len(current_cluster)

        distance = abs(price - reference) / reference

        if distance <= tolerance:

            current_cluster.append(price)

        else:

            clusters.append(current_cluster)
            current_cluster = [price]

    clusters.append(current_cluster)

    return clusters


# ============================================================
# SUPPORT / RESISTANCE
# ============================================================

def find_support_resistance(
    df,
    structure_points,
    tolerance=0.003,
    max_levels=3,
):
    """
    Find meaningful support/resistance zones.

    Only structure points are used.
    """

    if not structure_points:

        return {
            "support": [],
            "resistance": [],
        }

    current_price = float(df["close"].iloc[-1])

    support_points = []
    resistance_points = []

    for point in structure_points:

        price = float(point["price"])

        if price < current_price:

            support_points.append(price)

        elif price > current_price:

            resistance_points.append(price)

    # --------------------------------------------------------
    # CLUSTER
    # --------------------------------------------------------

    support_clusters = _cluster_levels(
        support_points,
        tolerance
    )

    resistance_clusters = _cluster_levels(
        resistance_points,
        tolerance
    )

    # --------------------------------------------------------
    # CREATE ZONES
    # --------------------------------------------------------

    def build_zone(cluster):

        if not cluster:
            return None

        center = sum(cluster) / len(cluster)

        low = min(cluster)
        high = max(cluster)

        touches = len(cluster)

        return {
            "price": round(center, 3),
            "low": round(low, 3),
            "high": round(high, 3),
            "touches": touches,
            "strength": touches,
        }

    supports = [
        build_zone(cluster)
        for cluster in support_clusters
    ]

    resistances = [
        build_zone(cluster)
        for cluster in resistance_clusters
    ]

    supports = [x for x in supports if x]
    resistances = [x for x in resistances if x]

    # --------------------------------------------------------
    # SUPPORT:
    # nearest to current price first
    # --------------------------------------------------------

    supports.sort(
        key=lambda x: x["price"],
        reverse=True
    )

    # --------------------------------------------------------
    # RESISTANCE:
    # nearest to current price first
    # --------------------------------------------------------

    resistances.sort(
        key=lambda x: x["price"]
    )

    supports = supports[:max_levels]
    resistances = resistances[:max_levels]

    return {
        "support": supports,
        "resistance": resistances,
    }


# ============================================================
# FULL STRUCTURE ANALYSIS
# ============================================================

def analyze_structure(df):
    """
    Complete market structure analysis.
    """

    swing_df = detect_swings(
        df,
        left=3,
        right=3
    )

    raw_points = get_swing_points(
        swing_df
    )

    structure_points = classify_market_structure(
        raw_points
    )

    trend = determine_structure_trend(
        structure_points
    )

    bos_events, choch_events = detect_structure_events(
        df,
        structure_points
    )

    levels = find_support_resistance(
        df,
        structure_points,
        tolerance=0.003,
        max_levels=3,
    )

    return {
        "trend": trend,
        "points": structure_points,
        "bos": bos_events,
        "choch": choch_events,
        "support": levels["support"],
        "resistance": levels["resistance"],
    }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    from data.market_data import (
        get_xauusd_historical_candles
    )

    print("=" * 70)
    print("XAU/USD MARKET STRUCTURE TEST")
    print("=" * 70)

    df = get_xauusd_historical_candles(
        interval="4h",
        required_bars=300
    )

    result = analyze_structure(df)

    print()
    print("Trend:", result["trend"])

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

    print()
    print("LAST STRUCTURE POINTS")

    for point in result["points"][-15:]:

        print(
            point["time"],
            "|",
            point["type"],
            "|",
            point["classification"],
            "|",
            f'{point["price"]:.3f}'
        )

    print()
    print("SUPPORT")

    for level in result["support"]:

        print(
            f'{level["price"]:.3f}',
            "| zone:",
            f'{level["low"]:.3f}',
            "-",
            f'{level["high"]:.3f}',
            "| touches=",
            level["touches"]
        )

    print()
    print("RESISTANCE")

    for level in result["resistance"]:

        print(
            f'{level["price"]:.3f}',
            "| zone:",
            f'{level["low"]:.3f}',
            "-",
            f'{level["high"]:.3f}',
            "| touches=",
            level["touches"]
        )

