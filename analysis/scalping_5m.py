import pandas as pd
import numpy as np


# ============================================================
# SETTINGS
# ============================================================

EMA_FAST = 20
EMA_MIDDLE = 50
EMA_SLOW = 200

RSI_PERIOD = 14
ATR_PERIOD = 14
ADX_PERIOD = 14

SWING_LEFT = 3
SWING_RIGHT = 3


# ============================================================
# SAFE NUMBER
# ============================================================

def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        value = float(value)

        if np.isnan(value):
            return default

        return value

    except Exception:

        return default


# ============================================================
# EMA
# ============================================================

def calculate_ema(series, period):

    return series.ewm(
        span=period,
        adjust=False
    ).mean()


# ============================================================
# RSI
# ============================================================

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        np.nan
    )

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi.fillna(50)


# ============================================================
# ATR
# ============================================================

def calculate_atr(df, period=14):

    previous_close = df["close"].shift(1)

    tr1 = df["high"] - df["low"]

    tr2 = (
        df["high"] - previous_close
    ).abs()

    tr3 = (
        df["low"] - previous_close
    ).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    atr = true_range.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    return atr


# ============================================================
# MACD
# ============================================================

def calculate_macd(
    series,
    fast=12,
    slow=26,
    signal=9
):

    ema_fast = series.ewm(
        span=fast,
        adjust=False
    ).mean()

    ema_slow = series.ewm(
        span=slow,
        adjust=False
    ).mean()

    macd = ema_fast - ema_slow

    macd_signal = macd.ewm(
        span=signal,
        adjust=False
    ).mean()

    histogram = macd - macd_signal

    return (
        macd,
        macd_signal,
        histogram
    )


# ============================================================
# ADX / DIRECTIONAL MOVEMENT
# ============================================================

def calculate_adx(
    df,
    period=14
):

    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()

    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where(
            (up_move > down_move) &
            (up_move > 0),
            up_move,
            0
        ),
        index=df.index
    )

    minus_dm = pd.Series(
        np.where(
            (down_move > up_move) &
            (down_move > 0),
            down_move,
            0
        ),
        index=df.index
    )

    previous_close = close.shift(1)

    tr1 = high - low

    tr2 = (
        high - previous_close
    ).abs()

    tr3 = (
        low - previous_close
    ).abs()

    true_range = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    atr = true_range.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    plus_di = (
        100 *
        plus_dm.ewm(
            alpha=1 / period,
            adjust=False
        ).mean() /
        atr.replace(0, np.nan)
    )

    minus_di = (
        100 *
        minus_dm.ewm(
            alpha=1 / period,
            adjust=False
        ).mean() /
        atr.replace(0, np.nan)
    )

    dx = (
        100 *
        (plus_di - minus_di).abs() /
        (plus_di + minus_di).replace(
            0,
            np.nan
        )
    )

    adx = dx.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    return (
        adx.fillna(0),
        plus_di.fillna(0),
        minus_di.fillna(0)
    )


# ============================================================
# SWING DETECTION
# ============================================================

def detect_swings(df):

    highs = df["high"].values

    lows = df["low"].values

    swing_highs = []

    swing_lows = []


    for i in range(
        SWING_LEFT,
        len(df) - SWING_RIGHT
    ):

        left_highs = highs[
            i - SWING_LEFT:i
        ]

        right_highs = highs[
            i + 1:
            i + 1 + SWING_RIGHT
        ]

        left_lows = lows[
            i - SWING_LEFT:i
        ]

        right_lows = lows[
            i + 1:
            i + 1 + SWING_RIGHT
        ]


        if (
            highs[i] > left_highs.max()
            and
            highs[i] > right_highs.max()
        ):

            swing_highs.append({
                "index": i,
                "price": float(highs[i])
            })


        if (
            lows[i] < left_lows.min()
            and
            lows[i] < right_lows.min()
        ):

            swing_lows.append({
                "index": i,
                "price": float(lows[i])
            })


    return (
        swing_highs,
        swing_lows
    )


# ============================================================
# MARKET STRUCTURE
# ============================================================

def analyze_structure(df):

    swing_highs, swing_lows = detect_swings(df)


    if len(swing_highs) < 2:
        high_structure = "UNKNOWN"

    else:

        h1 = swing_highs[-2]["price"]
        h2 = swing_highs[-1]["price"]

        if h2 > h1:
            high_structure = "HH"
        else:
            high_structure = "LH"


    if len(swing_lows) < 2:
        low_structure = "UNKNOWN"

    else:

        l1 = swing_lows[-2]["price"]
        l2 = swing_lows[-1]["price"]

        if l2 > l1:
            low_structure = "HL"
        else:
            low_structure = "LL"


    if (
        high_structure == "HH"
        and
        low_structure == "HL"
    ):

        trend = "BULLISH"


    elif (
        high_structure == "LH"
        and
        low_structure == "LL"
    ):

        trend = "BEARISH"


    else:

        trend = "NEUTRAL"


    return {
        "trend": trend,
        "high_structure": high_structure,
        "low_structure": low_structure,
        "swing_highs": swing_highs,
        "swing_lows": swing_lows
    }


# ============================================================
# BOS DETECTION
# ============================================================

def detect_bos(
    df,
    structure
):

    if len(df) < 2:
        return "NONE"


    last_close = safe_float(
        df.iloc[-1]["close"]
    )


    swing_highs = structure[
        "swing_highs"
    ]

    swing_lows = structure[
        "swing_lows"
    ]


    if swing_highs:

        last_high = swing_highs[-1]["price"]

        if last_close > last_high:

            return "BULLISH"


    if swing_lows:

        last_low = swing_lows[-1]["price"]

        if last_close < last_low:

            return "BEARISH"


    return "NONE"


# ============================================================
# LIQUIDITY SWEEP
# ============================================================

def detect_liquidity_sweep(
    df,
    structure
):

    if len(df) < 2:
        return "NONE"


    current = df.iloc[-1]

    previous = df.iloc[-2]


    swing_highs = structure[
        "swing_highs"
    ]

    swing_lows = structure[
        "swing_lows"
    ]


    # Sweep previous swing high
    if swing_highs:

        last_high = swing_highs[-1]["price"]

        if (
            current["high"] > last_high
            and
            current["close"] < last_high
        ):

            return "BEARISH_SWEEP"


    # Sweep previous swing low
    if swing_lows:

        last_low = swing_lows[-1]["price"]

        if (
            current["low"] < last_low
            and
            current["close"] > last_low
        ):

            return "BULLISH_SWEEP"


    # Short-term previous candle sweep
    if (
        current["high"] > previous["high"]
        and
        current["close"] < previous["high"]
    ):

        return "BEARISH_SWEEP"


    if (
        current["low"] < previous["low"]
        and
        current["close"] > previous["low"]
    ):

        return "BULLISH_SWEEP"


    return "NONE"


# ============================================================
# INDICATOR DIRECTION
# ============================================================

def determine_indicator_direction(
    df
):

    last = df.iloc[-1]


    price = safe_float(last["close"])

    ema20 = safe_float(last["ema20"])
    ema50 = safe_float(last["ema50"])
    ema200 = safe_float(last["ema200"])

    rsi = safe_float(last["rsi"])

    macd = safe_float(last["macd"])
    macd_signal = safe_float(
        last["macd_signal"]
    )

    plus_di = safe_float(
        last["plus_di"]
    )

    minus_di = safe_float(
        last["minus_di"]
    )


    bullish_score = 0
    bearish_score = 0


    # EMA 20 / 50
    if price > ema20:
        bullish_score += 1

    elif price < ema20:
        bearish_score += 1


    if ema20 > ema50:
        bullish_score += 2

    elif ema20 < ema50:
        bearish_score += 2


    # EMA 200
    if price > ema200:
        bullish_score += 1

    elif price < ema200:
        bearish_score += 1


    # RSI
    if rsi >= 55:
        bullish_score += 2

    elif rsi <= 45:
        bearish_score += 2


    # MACD
    if macd > macd_signal:
        bullish_score += 1

    elif macd < macd_signal:
        bearish_score += 1


    # DMI
    if plus_di > minus_di:
        bullish_score += 1

    elif plus_di < minus_di:
        bearish_score += 1


    if bullish_score > bearish_score:

        direction = "BULLISH"

    elif bearish_score > bullish_score:

        direction = "BEARISH"

    else:

        direction = "NEUTRAL"


    return {
        "direction": direction,
        "bullish_score": bullish_score,
        "bearish_score": bearish_score
    }


# ============================================================
# MAIN 5M ANALYSIS
# ============================================================

def analyze_5m(df):

    if df is None or df.empty:

        return {
            "status": "ERROR",
            "message": "5M data mavjud emas."
        }


    required_columns = {
        "open",
        "high",
        "low",
        "close"
    }


    missing = (
        required_columns -
        set(df.columns)
    )


    if missing:

        return {
            "status": "ERROR",
            "message": (
                "Yetishmayotgan ustunlar: "
                f"{sorted(missing)}"
            )
        }


    # Copy
    data = df.copy()


    # Numeric conversion
    for column in [
        "open",
        "high",
        "low",
        "close"
    ]:

        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )


    data = data.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close"
        ]
    )


    if len(data) < 220:

        return {
            "status": "ERROR",
            "message": (
                "5M analysis uchun kamida "
                "220 candle kerak. "
                f"Hozir: {len(data)}"
            )
        }


    # ========================================================
    # Indicators
    # ========================================================

    data["ema20"] = calculate_ema(
        data["close"],
        EMA_FAST
    )

    data["ema50"] = calculate_ema(
        data["close"],
        EMA_MIDDLE
    )

    data["ema200"] = calculate_ema(
        data["close"],
        EMA_SLOW
    )


    data["rsi"] = calculate_rsi(
        data["close"],
        RSI_PERIOD
    )


    data["atr"] = calculate_atr(
        data,
        ATR_PERIOD
    )


    (
        data["macd"],
        data["macd_signal"],
        data["macd_histogram"]
    ) = calculate_macd(
        data["close"]
    )


    (
        data["adx"],
        data["plus_di"],
        data["minus_di"]
    ) = calculate_adx(
        data,
        ADX_PERIOD
    )


    # ========================================================
    # Structure
    # ========================================================

    structure = analyze_structure(
        data
    )


    bos = detect_bos(
        data,
        structure
    )


    liquidity_sweep = (
        detect_liquidity_sweep(
            data,
            structure
        )
    )


    # ========================================================
    # Indicator direction
    # ========================================================

    indicator = (
        determine_indicator_direction(
            data
        )
    )


    last = data.iloc[-1]


    price = safe_float(
        last["close"]
    )

    atr = safe_float(
        last["atr"]
    )

    rsi = safe_float(
        last["rsi"]
    )

    adx = safe_float(
        last["adx"]
    )


    # ========================================================
    # Strength
    # ========================================================

    if adx >= 25:

        strength = "STRONG"

    elif adx >= 20:

        strength = "MODERATE"

    else:

        strength = "WEAK"


    # ========================================================
    # Setup detection
    # ========================================================

    setup = "NONE"


    if (
        structure["trend"] == "BULLISH"
        and
        indicator["direction"] == "BULLISH"
    ):

        setup = "BULLISH_ALIGNMENT"


    elif (
        structure["trend"] == "BEARISH"
        and
        indicator["direction"] == "BEARISH"
    ):

        setup = "BEARISH_ALIGNMENT"


    if liquidity_sweep == "BULLISH_SWEEP":

        setup = "BULLISH_LIQUIDITY_SWEEP"


    elif liquidity_sweep == "BEARISH_SWEEP":

        setup = "BEARISH_LIQUIDITY_SWEEP"


    # ========================================================
    # Result
    # ========================================================

    return {

        "status": "OK",

        "timeframe": "5m",

        "price": price,

        "atr": atr,

        "rsi": rsi,

        "adx": adx,

        "strength": strength,

        "direction": indicator[
            "direction"
        ],

        "bullish_score": indicator[
            "bullish_score"
        ],

        "bearish_score": indicator[
            "bearish_score"
        ],

        "structure": structure[
            "trend"
        ],

        "high_structure": structure[
            "high_structure"
        ],

        "low_structure": structure[
            "low_structure"
        ],

        "bos": bos,

        "liquidity_sweep":
            liquidity_sweep,

        "setup": setup,

        "ema20": safe_float(
            last["ema20"]
        ),

        "ema50": safe_float(
            last["ema50"]
        ),

        "ema200": safe_float(
            last["ema200"]
        ),

        "macd": safe_float(
            last["macd"]
        ),

        "macd_signal": safe_float(
            last["macd_signal"]
        ),

        "plus_di": safe_float(
            last["plus_di"]
        ),

        "minus_di": safe_float(
            last["minus_di"]
        )
    }


# ============================================================
# FORMAT RESULT
# ============================================================

def format_5m_analysis(result):

    if result.get("status") != "OK":

        return (
            "5M SCALPING ANALYSIS\n"
            "--------------------\n"
            f"ERROR: {result.get('message')}"
        )


    lines = [

        "",
        "=" * 60,
        "XAU/USD 5M SCALPING ANALYSIS",
        "=" * 60,

        f"PRICE: {result['price']:.3f}",

        "",

        "DIRECTION",
        "--------------------",
        f"Direction : {result['direction']}",
        f"Strength  : {result['strength']}",

        "",

        "INDICATORS",
        "--------------------",
        f"EMA20     : {result['ema20']:.3f}",
        f"EMA50     : {result['ema50']:.3f}",
        f"EMA200    : {result['ema200']:.3f}",
        f"RSI       : {result['rsi']:.2f}",
        f"MACD      : {result['macd']:.4f}",
        f"MACD Sig  : {result['macd_signal']:.4f}",
        f"ADX       : {result['adx']:.2f}",

        "",

        "STRUCTURE",
        "--------------------",
        f"Trend     : {result['structure']}",
        f"High      : {result['high_structure']}",
        f"Low       : {result['low_structure']}",
        f"BOS       : {result['bos']}",

        "",

        "LIQUIDITY",
        "--------------------",
        f"Sweep     : {result['liquidity_sweep']}",

        "",

        "SETUP",
        "--------------------",
        f"{result['setup']}",

        "",

        "SCORE",
        "--------------------",
        f"Bullish   : {result['bullish_score']}",
        f"Bearish   : {result['bearish_score']}",

        "=" * 60
    ]


    return "\n".join(lines)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "5M Scalping Engine V1"
    )

    print(
        "Module successfully loaded."
    )
