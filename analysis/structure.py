import sys
from pathlib import Path

# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd


# ============================================================
# 1. SWING HIGH / SWING LOW
# ============================================================

def detect_swings(df, left=3, right=3):
    """
    Swing High va Swing Low ni aniqlaydi.

    Swing faqat right candle o'tgandan keyin tasdiqlanadi.
    Shu sababli real-time tahlilda kelajak ma'lumotidan
    noto'g'ri foydalanish kamayadi.

    swing_high:
        True -> Swing High

    swing_low:
        True -> Swing Low

    swing_confirmed_at:
        Ushbu swing qaysi candle'da tasdiqlanganini bildiradi.
    """

    df = df.copy()

    df["swing_high"] = False
    df["swing_low"] = False

    df["swing_high_confirmed_at"] = None
    df["swing_low_confirmed_at"] = None

    for i in range(left, len(df) - right):

        current_high = float(df.iloc[i]["high"])
        current_low = float(df.iloc[i]["low"])

        left_highs = df.iloc[i - left:i]["high"]
        right_highs = df.iloc[i + 1:i + right + 1]["high"]

        left_lows = df.iloc[i - left:i]["low"]
        right_lows = df.iloc[i + 1:i + right + 1]["low"]

        # ----------------------------------------------------
        # SWING HIGH
        # ----------------------------------------------------

        if (
            current_high > left_highs.max()
            and current_high > right_highs.max()
        ):

            df.loc[df.index[i], "swing_high"] = True

            confirmation_index = i + right

            df.loc[
                df.index[i],
                "swing_high_confirmed_at"
            ] = confirmation_index

        # ----------------------------------------------------
        # SWING LOW
        # ----------------------------------------------------

        if (
            current_low < left_lows.min()
            and current_low < right_lows.min()
        ):

            df.loc[df.index[i], "swing_low"] = True

            confirmation_index = i + right

            df.loc[
                df.index[i],
                "swing_low_confirmed_at"
            ] = confirmation_index

    return df


# ============================================================
# 2. SWING POINTLAR
# ============================================================

def get_swing_points(df):
    """
    Tasdiqlangan barcha swing nuqtalarni qaytaradi.

    Har bir point:

        index
        confirmation_index
        time
        type
        price
    """

    points = []

    for index, row in df.iterrows():

        if row["swing_high"]:

            confirmation_index = row[
                "swing_high_confirmed_at"
            ]

            points.append({
                "index": int(index),
                "confirmation_index": int(confirmation_index),
                "time": row["openTime"],
                "type": "HIGH",
                "price": float(row["high"])
            })

        if row["swing_low"]:

            confirmation_index = row[
                "swing_low_confirmed_at"
            ]

            points.append({
                "index": int(index),
                "confirmation_index": int(confirmation_index),
                "time": row["openTime"],
                "type": "LOW",
                "price": float(row["low"])
            })

    points.sort(
        key=lambda x: x["index"]
    )

    return points


# ============================================================
# 3. HH / HL / LH / LL
# ============================================================

def classify_market_structure(df):
    """
    Swing pointlarni:

        HH = Higher High
        HL = Higher Low
        LH = Lower High
        LL = Lower Low

    sifatida klassifikatsiya qiladi.

    Bu klassifikatsiya faqat o'z turidagi oldingi
    swing bilan taqqoslanadi.
    """

    swing_points = get_swing_points(df)

    classified = []

    previous_high = None
    previous_low = None

    for point in swing_points:

        item = point.copy()

        # ----------------------------------------------------
        # HIGH
        # ----------------------------------------------------

        if point["type"] == "HIGH":

            if previous_high is None:

                item["structure"] = "FIRST_HIGH"

            elif point["price"] > previous_high:

                item["structure"] = "HH"

            else:

                item["structure"] = "LH"

            previous_high = point["price"]

        # ----------------------------------------------------
        # LOW
        # ----------------------------------------------------

        elif point["type"] == "LOW":

            if previous_low is None:

                item["structure"] = "FIRST_LOW"

            elif point["price"] > previous_low:

                item["structure"] = "HL"

            else:

                item["structure"] = "LL"

            previous_low = point["price"]

        classified.append(item)

    return classified


# ============================================================
# 4. STRUCTURE TREND
# ============================================================

def determine_structure_trend(structure_points):
    """
    Oxirgi structure pointlar asosida trendni aniqlaydi.
    """

    if not structure_points:
        return "NEUTRAL"

    recent = structure_points[-12:]

    hh_count = sum(
        1 for p in recent
        if p["structure"] == "HH"
    )

    hl_count = sum(
        1 for p in recent
        if p["structure"] == "HL"
    )

    lh_count = sum(
        1 for p in recent
        if p["structure"] == "LH"
    )

    ll_count = sum(
        1 for p in recent
        if p["structure"] == "LL"
    )

    bullish_score = hh_count + hl_count
    bearish_score = lh_count + ll_count

    if bullish_score > bearish_score:
        return "BULLISH"

    if bearish_score > bullish_score:
        return "BEARISH"

    return "NEUTRAL"


# ============================================================
# 5. CAUSAL STRUCTURE TREND
# ============================================================

def _get_initial_trend(available_points):
    """
    Faqat o'sha vaqtgacha ma'lum bo'lgan structure pointlar
    asosida boshlang'ich trendni aniqlaydi.

    Kelajakdagi swing ishlatilmaydi.
    """

    highs = [
        p for p in available_points
        if p["type"] == "HIGH"
    ]

    lows = [
        p for p in available_points
        if p["type"] == "LOW"
    ]

    if len(highs) < 2 or len(lows) < 2:
        return "NEUTRAL"

    previous_high = highs[-2]
    latest_high = highs[-1]

    previous_low = lows[-2]
    latest_low = lows[-1]

    higher_high = (
        latest_high["price"]
        > previous_high["price"]
    )

    higher_low = (
        latest_low["price"]
        > previous_low["price"]
    )

    lower_high = (
        latest_high["price"]
        < previous_high["price"]
    )

    lower_low = (
        latest_low["price"]
        < previous_low["price"]
    )

    if higher_high and higher_low:
        return "BULLISH"

    if lower_high and lower_low:
        return "BEARISH"

    return "NEUTRAL"


# ============================================================
# 6. BOS + CHOCH
# ============================================================

def detect_structure_events(df, structure_points):
    """
    BOS va CHOCH ni real-timega yaqin causal usulda aniqlaydi.

    Qoidalar:

    BULLISH trend:
        close > oxirgi tasdiqlangan swing high
            -> BULLISH BOS

        close < oxirgi tasdiqlangan swing low
            -> BEARISH CHOCH

    BEARISH trend:
        close < oxirgi tasdiqlangan swing low
            -> BEARISH BOS

        close > oxirgi tasdiqlangan swing high
            -> BULLISH CHOCH

    NEUTRAL:
        kuchli breakout trendni boshlashi mumkin.

    Bir xil swing level qayta-qayta signal bermaydi.
    """

    if not structure_points:
        return []

    events = []

    current_trend = "NEUTRAL"

    broken_highs = set()
    broken_lows = set()

    # Eng oxirgi tasdiqlangan swinglar
    active_high = None
    active_low = None

    # ========================================================
    # HAR BIR CANDLE BO'YICHA
    # ========================================================

    for i in range(len(df)):

        row = df.iloc[i]

        close = float(row["close"])

        # ----------------------------------------------------
        # Shu candle vaqtigacha TASDIQLANGAN swinglar
        # ----------------------------------------------------

        available_points = [
            p for p in structure_points
            if p["confirmation_index"] <= i
        ]

        # ----------------------------------------------------
        # Yangi HIGH / LOW larni olish
        # ----------------------------------------------------

        available_highs = [
            p for p in available_points
            if p["type"] == "HIGH"
        ]

        available_lows = [
            p for p in available_points
            if p["type"] == "LOW"
        ]

        if available_highs:

            active_high = available_highs[-1]

        if available_lows:

            active_low = available_lows[-1]

        # ----------------------------------------------------
        # Boshlang'ich trend
        # ----------------------------------------------------

        if current_trend == "NEUTRAL":

            current_trend = _get_initial_trend(
                available_points
            )

        # ====================================================
        # BULLISH TREND
        # ====================================================

        if current_trend == "BULLISH":

            # ------------------------------------------------
            # BEARISH CHOCH
            # ------------------------------------------------

            if (
                active_low is not None
                and active_low["index"] not in broken_lows
                and close < active_low["price"]
            ):

                events.append({
                    "time": row["openTime"],
                    "type": "BEARISH_CHOCH",
                    "price": close,
                    "broken_level": active_low["price"],
                    "swing_time": active_low["time"]
                })

                broken_lows.add(
                    active_low["index"]
                )

                current_trend = "BEARISH"

                continue

            # ------------------------------------------------
            # BULLISH BOS
            # ------------------------------------------------

            if (
                active_high is not None
                and active_high["index"] not in broken_highs
                and close > active_high["price"]
            ):

                events.append({
                    "time": row["openTime"],
                    "type": "BULLISH_BOS",
                    "price": close,
                    "broken_level": active_high["price"],
                    "swing_time": active_high["time"]
                })

                broken_highs.add(
                    active_high["index"]
                )

        # ====================================================
        # BEARISH TREND
        # ====================================================

        elif current_trend == "BEARISH":

            # ------------------------------------------------
            # BULLISH CHOCH
            # ------------------------------------------------

            if (
                active_high is not None
                and active_high["index"] not in broken_highs
                and close > active_high["price"]
            ):

                events.append({
                    "time": row["openTime"],
                    "type": "BULLISH_CHOCH",
                    "price": close,
                    "broken_level": active_high["price"],
                    "swing_time": active_high["time"]
                })

                broken_highs.add(
                    active_high["index"]
                )

                current_trend = "BULLISH"

                continue

            # ------------------------------------------------
            # BEARISH BOS
            # ------------------------------------------------

            if (
                active_low is not None
                and active_low["index"] not in broken_lows
                and close < active_low["price"]
            ):

                events.append({
                    "time": row["openTime"],
                    "type": "BEARISH_BOS",
                    "price": close,
                    "broken_level": active_low["price"],
                    "swing_time": active_low["time"]
                })

                broken_lows.add(
                    active_low["index"]
                )

        # ====================================================
        # NEUTRAL HOLAT
        # ====================================================

        else:

            # Bullish breakout
            if (
                active_high is not None
                and active_high["index"] not in broken_highs
                and close > active_high["price"]
            ):

                events.append({
                    "time": row["openTime"],
                    "type": "INITIAL_BULLISH_BOS",
                    "price": close,
                    "broken_level": active_high["price"],
                    "swing_time": active_high["time"]
                })

                broken_highs.add(
                    active_high["index"]
                )

                current_trend = "BULLISH"

                continue

            # Bearish breakout
            if (
                active_low is not None
                and active_low["index"] not in broken_lows
                and close < active_low["price"]
            ):

                events.append({
                    "time": row["openTime"],
                    "type": "INITIAL_BEARISH_BOS",
                    "price": close,
                    "broken_level": active_low["price"],
                    "swing_time": active_low["time"]
                })

                broken_lows.add(
                    active_low["index"]
                )

                current_trend = "BEARISH"

    return events


# ============================================================
# 7. BOS VA CHOCH ALOHIDA OLISH
# ============================================================

def detect_bos(df, structure_points):
    """
    Faqat BOS hodisalarini qaytaradi.
    """

    events = detect_structure_events(
        df,
        structure_points
    )

    return [
        event
        for event in events
        if "BOS" in event["type"]
    ]


def detect_choch(df, structure_points):
    """
    Faqat CHOCH hodisalarini qaytaradi.
    """

    events = detect_structure_events(
        df,
        structure_points
    )

    return [
        event
        for event in events
        if "CHOCH" in event["type"]
    ]


# ============================================================
# 8. SUPPORT / RESISTANCE
# ============================================================

def find_support_resistance(
    df,
    max_levels=5,
    tolerance=0.002
):
    """
    Swing High / Swing Low asosida
    Support va Resistance levelarni topadi.

    tolerance:
        Bir-biriga yaqin levelarni bitta cluster qilish.

        0.002 = 0.2%
    """

    structure_points = classify_market_structure(df)

    current_price = float(
        df.iloc[-1]["close"]
    )

    highs = [
        p["price"]
        for p in structure_points
        if p["type"] == "HIGH"
    ]

    lows = [
        p["price"]
        for p in structure_points
        if p["type"] == "LOW"
    ]

    # ========================================================
    # LEVEL CLUSTER
    # ========================================================

    def cluster_levels(levels):

        if not levels:
            return []

        levels = sorted(levels)

        clusters = []

        for level in levels:

            added = False

            for cluster in clusters:

                average = sum(cluster) / len(cluster)

                distance = (
                    abs(level - average)
                    / average
                )

                if distance <= tolerance:

                    cluster.append(level)

                    added = True

                    break

            if not added:

                clusters.append([level])

        result = []

        for cluster in clusters:

            average = (
                sum(cluster)
                / len(cluster)
            )

            result.append({
                "price": average,
                "touches": len(cluster)
            })

        return result

    all_resistance = cluster_levels(highs)
    all_support = cluster_levels(lows)

    # ========================================================
    # PRICE BO'YICHA AJRATISH
    # ========================================================

    resistance = [
        level
        for level in all_resistance
        if level["price"] > current_price
    ]

    support = [
        level
        for level in all_support
        if level["price"] < current_price
    ]

    # Eng yaqin levelardan boshlab
    resistance.sort(
        key=lambda x: x["price"]
    )

    support.sort(
        key=lambda x: x["price"],
        reverse=True
    )

    resistance = resistance[:max_levels]
    support = support[:max_levels]

    return {
        "support": support,
        "resistance": resistance
    }


# ============================================================
# 9. TO'LIQ MARKET STRUCTURE TAHLILI
# ============================================================

def analyze_structure(
    df,
    left=3,
    right=3
):
    """
    Bitta timeframe uchun to'liq
    Market Structure Analysis.
    """

    df = detect_swings(
        df,
        left=left,
        right=right
    )

    structure_points = classify_market_structure(
        df
    )

    trend = determine_structure_trend(
        structure_points
    )

    structure_events = detect_structure_events(
        df,
        structure_points
    )

    bos = [
        event
        for event in structure_events
        if "BOS" in event["type"]
    ]

    choch = [
        event
        for event in structure_events
        if "CHOCH" in event["type"]
    ]

    support_resistance = find_support_resistance(
        df
    )

    return {
        "trend": trend,
        "structure_points": structure_points,
        "events": structure_events,
        "bos": bos,
        "choch": choch,
        "support": support_resistance["support"],
        "resistance": support_resistance["resistance"],
        "data": df
    }


# ============================================================
# 10. TEST
# ============================================================

if __name__ == "__main__":

    from data.market_data import get_xauusd_candles

    print("=" * 70)
    print("XAU/USD MARKET STRUCTURE TEST")
    print("=" * 70)

    # 4H ma'lumot
    df = get_xauusd_candles(
        interval="4h",
        limit=250
    )

    print(
        f"\nCandle soni: {len(df)}"
    )

    # ========================================================
    # ANALYSIS
    # ========================================================

    result = analyze_structure(
        df,
        left=3,
        right=3
    )

    # ========================================================
    # TREND
    # ========================================================

    print("\n" + "=" * 70)
    print("MARKET STRUCTURE TREND")
    print("=" * 70)

    print(
        "Trend:",
        result["trend"]
    )

    # ========================================================
    # STRUCTURE POINTS
    # ========================================================

    print("\n" + "=" * 70)
    print("OXIRGI STRUCTURE POINTLAR")
    print("=" * 70)

    for point in result[
        "structure_points"
    ][-15:]:

        print(
            f"{point['time']} | "
            f"{point['type']:4} | "
            f"{point['structure']:10} | "
            f"{point['price']:.2f} | "
            f"ConfirmIndex: "
            f"{point['confirmation_index']}"
        )

    # ========================================================
    # BOS
    # ========================================================

    print("\n" + "=" * 70)
    print("BOS")
    print("=" * 70)

    if result["bos"]:

        for event in result["bos"][-10:]:

            print(
                f"{event['time']} | "
                f"{event['type']:22} | "
                f"Price: "
                f"{event['price']:.2f} | "
                f"Broken: "
                f"{event['broken_level']:.2f} | "
                f"Swing: "
                f"{event['swing_time']}"
            )

    else:

        print("BOS topilmadi.")

    # ========================================================
    # CHOCH
    # ========================================================

    print("\n" + "=" * 70)
    print("CHOCH")
    print("=" * 70)

    if result["choch"]:

        for event in result["choch"][-10:]:

            print(
                f"{event['time']} | "
                f"{event['type']:22} | "
                f"Price: "
                f"{event['price']:.2f} | "
                f"Broken: "
                f"{event['broken_level']:.2f} | "
                f"Swing: "
                f"{event['swing_time']}"
            )

    else:

        print("CHOCH topilmadi.")

    # ========================================================
    # SUPPORT
    # ========================================================

    print("\n" + "=" * 70)
    print("SUPPORT")
    print("=" * 70)

    if result["support"]:

        for level in result["support"]:

            print(
                f"Support: "
                f"{level['price']:.2f} | "
                f"Touches: "
                f"{level['touches']}"
            )

    else:

        print("Support topilmadi.")

    # ========================================================
    # RESISTANCE
    # ========================================================

    print("\n" + "=" * 70)
    print("RESISTANCE")
    print("=" * 70)

    if result["resistance"]:

        for level in result["resistance"]:

            print(
                f"Resistance: "
                f"{level['price']:.2f} | "
                f"Touches: "
                f"{level['touches']}"
            )

    else:

        print("Resistance topilmadi.")

    # ========================================================
    # FINAL
    # ========================================================

    print("\n" + "=" * 70)
    print("MARKET STRUCTURE TEST YAKUNLANDI")
    print("=" * 70)