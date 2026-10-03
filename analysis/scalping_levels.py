import pandas as pd


# ============================================================
# SETTINGS
# ============================================================

TP1_RR = 1.5
TP2_RR = 2.5

ATR_SL_MULTIPLIER = 1.20
SWEEP_BUFFER_ATR = 0.15

MIN_RISK = 0.50


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        result = float(value)

        if pd.isna(result):
            return default

        return result

    except (TypeError, ValueError):
        return default


def normalize_direction(direction):
    if direction is None:
        return "NONE"

    direction = str(direction).upper().strip()

    if direction in ("BUY", "BULLISH", "LONG"):
        return "BUY"

    if direction in ("SELL", "BEARISH", "SHORT"):
        return "SELL"

    return "NONE"


def get_last_closed_candle(df):
    """
    Returns the latest CLOSED 5M candle.

    If is_open column exists:
        is_open == 0 -> closed candle

    Otherwise:
        last row is used.
    """

    if df is None or df.empty:
        return None

    data = df.copy()

    if "is_open" in data.columns:

        closed = data[data["is_open"] == 0]

        if not closed.empty:
            return closed.iloc[-1]

    return data.iloc[-1]


def get_recent_high(df, lookback=20):
    """
    Returns recent high from closed candles.
    """

    if df is None or df.empty:
        return None

    data = df.copy()

    if "is_open" in data.columns:
        data = data[data["is_open"] == 0]

    if data.empty:
        return None

    data = data.tail(lookback)

    return safe_float(data["high"].max(), None)


def get_recent_low(df, lookback=20):
    """
    Returns recent low from closed candles.
    """

    if df is None or df.empty:
        return None

    data = df.copy()

    if "is_open" in data.columns:
        data = data[data["is_open"] == 0]

    if data.empty:
        return None

    data = data.tail(lookback)

    return safe_float(data["low"].min(), None)


# ============================================================
# STOP LOSS
# ============================================================

def calculate_stop_loss(
    direction,
    entry,
    atr,
    df,
    liquidity_sweep=None
):
    """
    Calculate protected 5M stop loss.

    SELL:
        SL above entry.

    BUY:
        SL below entry.

    ATR is the primary protection.
    Liquidity sweep can provide an additional structural level.
    """

    direction = normalize_direction(direction)

    entry = safe_float(entry)
    atr = safe_float(atr)

    if direction == "NONE":
        return None, 0.0, "INVALID_DIRECTION"

    if entry <= 0:
        return None, 0.0, "INVALID_ENTRY"

    if atr <= 0:
        return None, 0.0, "INVALID_ATR"

    # --------------------------------------------------------
    # Minimum allowed risk
    # --------------------------------------------------------

    minimum_risk = max(
        MIN_RISK,
        atr * 0.50
    )

    atr_risk = max(
        atr * ATR_SL_MULTIPLIER,
        minimum_risk
    )

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    if direction == "SELL":

        atr_sl = entry + atr_risk

        recent_high = get_recent_high(df)

        structural_sl = None

        if recent_high is not None:

            structural_sl = (
                recent_high +
                atr * SWEEP_BUFFER_ATR
            )

        # If bearish liquidity sweep exists,
        # structural high becomes important.
        if liquidity_sweep == "BEARISH_SWEEP" and structural_sl:

            candidates = [
                atr_sl,
                structural_sl
            ]

            valid_candidates = [
                level
                for level in candidates
                if level > entry + minimum_risk
            ]

            if valid_candidates:

                # Closest valid protected SL
                stop_loss = min(valid_candidates)

                method = "ATR + BEARISH_SWEEP"

            else:

                stop_loss = atr_sl
                method = "ATR"

        else:

            stop_loss = atr_sl
            method = "ATR"

        risk = stop_loss - entry

        return (
            round(stop_loss, 3),
            round(risk, 3),
            method
        )

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    if direction == "BUY":

        atr_sl = entry - atr_risk

        recent_low = get_recent_low(df)

        structural_sl = None

        if recent_low is not None:

            structural_sl = (
                recent_low -
                atr * SWEEP_BUFFER_ATR
            )

        if liquidity_sweep == "BULLISH_SWEEP" and structural_sl:

            candidates = [
                atr_sl,
                structural_sl
            ]

            valid_candidates = [
                level
                for level in candidates
                if level < entry - minimum_risk
            ]

            if valid_candidates:

                # Closest valid protected SL
                stop_loss = max(valid_candidates)

                method = "ATR + BULLISH_SWEEP"

            else:

                stop_loss = atr_sl
                method = "ATR"

        else:

            stop_loss = atr_sl
            method = "ATR"

        risk = entry - stop_loss

        return (
            round(stop_loss, 3),
            round(risk, 3),
            method
        )

    return None, 0.0, "INVALID_DIRECTION"


# ============================================================
# TAKE PROFITS
# ============================================================

def calculate_take_profits(
    direction,
    entry,
    risk
):
    """
    Calculate TP1 and TP2 using fixed Risk/Reward.

    TP1 = 1.5R
    TP2 = 2.5R
    """

    direction = normalize_direction(direction)

    entry = safe_float(entry)
    risk = safe_float(risk)

    if direction == "NONE":
        return None, None

    if entry <= 0 or risk <= 0:
        return None, None

    if direction == "SELL":

        tp1 = entry - risk * TP1_RR
        tp2 = entry - risk * TP2_RR

    elif direction == "BUY":

        tp1 = entry + risk * TP1_RR
        tp2 = entry + risk * TP2_RR

    else:
        return None, None

    return (
        round(tp1, 3),
        round(tp2, 3)
    )


# ============================================================
# MAIN LEVEL GENERATOR
# ============================================================

def generate_scalping_levels(
    df,
    analysis_result
):
    """
    Generate:

        ENTRY
        STOP LOSS
        TP1
        TP2
        RISK
        RR
        SL METHOD

    from the 5M analysis.
    """

    # --------------------------------------------------------
    # Validate dataframe
    # --------------------------------------------------------

    if df is None or df.empty:

        return {
            "status": "WAIT",
            "reason": "NO_5M_DATA"
        }

    if analysis_result is None:

        return {
            "status": "WAIT",
            "reason": "NO_ANALYSIS"
        }

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    direction = normalize_direction(
        analysis_result.get("direction")
    )

    if direction == "NONE":

        return {
            "status": "WAIT",
            "reason": "NO_VALID_DIRECTION"
        }

    # --------------------------------------------------------
    # Last closed candle
    # --------------------------------------------------------

    candle = get_last_closed_candle(df)

    if candle is None:

        return {
            "status": "WAIT",
            "reason": "NO_CLOSED_CANDLE"
        }

    entry = safe_float(
        candle.get("close")
    )

    if entry <= 0:

        return {
            "status": "WAIT",
            "reason": "INVALID_ENTRY"
        }

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

    atr = safe_float(
        analysis_result.get("atr")
    )

    if atr <= 0:

        return {
            "status": "WAIT",
            "reason": "INVALID_ATR"
        }

    # --------------------------------------------------------
    # Liquidity
    # --------------------------------------------------------

    liquidity_sweep = analysis_result.get(
        "liquidity_sweep"
    )

    if liquidity_sweep is not None:
        liquidity_sweep = str(
            liquidity_sweep
        ).upper()

    # --------------------------------------------------------
    # Stop loss
    # --------------------------------------------------------

    stop_loss, risk, sl_method = calculate_stop_loss(
        direction=direction,
        entry=entry,
        atr=atr,
        df=df,
        liquidity_sweep=liquidity_sweep
    )

    if stop_loss is None or risk <= 0:

        return {
            "status": "WAIT",
            "reason": "INVALID_STOP_LOSS"
        }

    # --------------------------------------------------------
    # Take profits
    # --------------------------------------------------------

    tp1, tp2 = calculate_take_profits(
        direction=direction,
        entry=entry,
        risk=risk
    )

    if tp1 is None or tp2 is None:

        return {
            "status": "WAIT",
            "reason": "INVALID_TAKE_PROFIT"
        }

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    candle_time = None

    if "open_time" in candle.index:

        candle_time = candle["open_time"]

    return {
        "status": "READY",

        "direction": direction,

        "entry": round(entry, 3),

        "stop_loss": round(stop_loss, 3),

        "tp1": round(tp1, 3),

        "tp2": round(tp2, 3),

        "risk": round(risk, 3),

        "rr_tp1": TP1_RR,

        "rr_tp2": TP2_RR,

        "atr": round(atr, 3),

        "sl_method": sl_method,

        "liquidity_sweep": liquidity_sweep,

        "candle_time": candle_time
    }


# ============================================================
# FORMAT OUTPUT
# ============================================================

def format_scalping_levels(levels):

    if levels is None:

        return """
============================================================
XAU/USD 5M SCALPING LEVELS
============================================================
STATUS: WAIT
============================================================
"""

    status = levels.get("status")

    if status != "READY":

        return f"""
============================================================
XAU/USD 5M SCALPING LEVELS
============================================================
STATUS: WAIT
REASON: {levels.get("reason", "UNKNOWN")}
============================================================
"""

    direction = levels.get("direction")

    entry = levels.get("entry")
    stop_loss = levels.get("stop_loss")
    tp1 = levels.get("tp1")
    tp2 = levels.get("tp2")
    risk = levels.get("risk")

    rr_tp1 = levels.get("rr_tp1")
    rr_tp2 = levels.get("rr_tp2")

    atr = levels.get("atr")
    sl_method = levels.get("sl_method")

    liquidity = levels.get(
        "liquidity_sweep"
    )

    candle_time = levels.get(
        "candle_time"
    )

    return f"""
============================================================
XAU/USD 5M SCALPING LEVELS
============================================================

STATUS: READY

DIRECTION
--------------------
{direction}

TRADE LEVELS
--------------------
ENTRY     : {entry}
STOP LOSS : {stop_loss}
TP1       : {tp1}
TP2       : {tp2}

RISK
--------------------
Risk      : {risk}
TP1 RR    : {rr_tp1}R
TP2 RR    : {rr_tp2}R

PROTECTION
--------------------
ATR       : {atr}
SL Method : {sl_method}
Liquidity : {liquidity}

CANDLE
--------------------
{candle_time}

============================================================
"""


# ============================================================
# MODULE TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("5M Entry / SL / TP Engine")
    print("=" * 60)

    print("Module loaded successfully.")

    print()
    print("Functions available:")
    print("- generate_scalping_levels()")
    print("- calculate_stop_loss()")
    print("- calculate_take_profits()")
    print("- format_scalping_levels()")
    print("=" * 60)
