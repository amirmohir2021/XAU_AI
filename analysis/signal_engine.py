from typing import Dict, Any


# ============================================================
# XAU/USD SIGNAL ENGINE V3.1
# ============================================================
#
# 1D  -> Major trend
# 4H  -> Market structure
# 1H  -> Confirmation / retracement
# 15M -> Entry trigger
#
# IMPORTANT:
# Technical alignment is NOT probability.
# It is only an internal scoring system.
# ============================================================


MIN_CONFIRMATIONS = 3

RR_TP1 = 1.5
RR_TP2 = 2.5

ATR_SL_MULTIPLIER = 1.20
STRUCTURE_BUFFER_ATR = 0.15

LEVEL_PROXIMITY_ATR = 0.50


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):

    try:
        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):

        return default


# ============================================================
# INDICATOR DIRECTION
# ============================================================

def get_indicator_direction(
    indicators: Dict[str, Any]
):

    bullish = 0
    bearish = 0

    reasons = []

    price = safe_float(
        indicators.get("price")
    )

    ema20 = safe_float(
        indicators.get("EMA20")
    )

    ema50 = safe_float(
        indicators.get("EMA50")
    )

    ema200 = safe_float(
        indicators.get("EMA200")
    )

    rsi = safe_float(
        indicators.get("RSI14")
    )

    macd = safe_float(
        indicators.get("MACD")
    )

    macd_signal = safe_float(
        indicators.get("MACD_SIGNAL")
    )

    di_plus = safe_float(
        indicators.get("DI_PLUS")
    )

    di_minus = safe_float(
        indicators.get("DI_MINUS")
    )

    adx = safe_float(
        indicators.get("ADX14")
    )

    # --------------------------------------------------------
    # PRICE / EMA20
    # --------------------------------------------------------

    if price and ema20:

        if price > ema20:

            bullish += 2

            reasons.append(
                "Price above EMA20"
            )

        elif price < ema20:

            bearish += 2

            reasons.append(
                "Price below EMA20"
            )

    # --------------------------------------------------------
    # EMA20 / EMA50
    # --------------------------------------------------------

    if ema20 and ema50:

        if ema20 > ema50:

            bullish += 2

            reasons.append(
                "EMA20 above EMA50"
            )

        elif ema20 < ema50:

            bearish += 2

            reasons.append(
                "EMA20 below EMA50"
            )

    # --------------------------------------------------------
    # PRICE / EMA200
    # --------------------------------------------------------

    if price and ema200:

        if price > ema200:

            bullish += 1

            reasons.append(
                "Price above EMA200"
            )

        elif price < ema200:

            bearish += 1

            reasons.append(
                "Price below EMA200"
            )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if rsi:

        if rsi >= 55:

            bullish += 2

            reasons.append(
                f"RSI bullish ({rsi:.1f})"
            )

        elif rsi <= 45:

            bearish += 2

            reasons.append(
                f"RSI bearish ({rsi:.1f})"
            )

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    if macd or macd_signal:

        if macd > macd_signal:

            bullish += 1

            reasons.append(
                "MACD bullish"
            )

        elif macd < macd_signal:

            bearish += 1

            reasons.append(
                "MACD bearish"
            )

    # --------------------------------------------------------
    # DMI
    # --------------------------------------------------------

    if di_plus or di_minus:

        if di_plus > di_minus:

            bullish += 1

            reasons.append(
                "DI+ above DI-"
            )

        elif di_minus > di_plus:

            bearish += 1

            reasons.append(
                "DI- above DI+"
            )

    # --------------------------------------------------------
    # DIRECTION
    # --------------------------------------------------------

    if bullish > bearish and bullish >= 5:

        direction = "BULLISH"

    elif bearish > bullish and bearish >= 5:

        direction = "BEARISH"

    else:

        direction = "NEUTRAL"

    # --------------------------------------------------------
    # STRENGTH
    # --------------------------------------------------------

    if adx >= 25:

        strength = "STRONG"

    elif adx >= 20:

        strength = "MODERATE"

    else:

        strength = "WEAK"

    return {
        "direction": direction,
        "bullish_score": bullish,
        "bearish_score": bearish,
        "strength": strength,
        "adx": adx,
        "reasons": reasons,
    }


# ============================================================
# MAJOR TREND
# ============================================================

def determine_major_trend(
    indicators
):

    result = get_indicator_direction(
        indicators
    )

    return result


# ============================================================
# 4H STRUCTURE
# ============================================================

def determine_structure_direction(
    structure_data
):

    if not structure_data:

        return {
            "direction": "NEUTRAL",
            "recent_bos": None,
            "recent_choch": None,
            "recent_bos_direction": None,
            "recent_choch_direction": None,
            "reasons": [],
        }

    trend = structure_data.get(
        "trend",
        "NEUTRAL"
    )

    bos_list = structure_data.get(
        "bos",
        []
    )

    choch_list = structure_data.get(
        "choch",
        []
    )

    # structure.py currently returns
    # BOS in chronological list order,
    # therefore find highest index as most recent.

    recent_bos = None

    if bos_list:

        recent_bos = max(
            bos_list,
            key=lambda x: x.get(
                "index",
                -1
            )
        )

    recent_choch = None

    if choch_list:

        recent_choch = max(
            choch_list,
            key=lambda x: x.get(
                "index",
                -1
            )
        )

    recent_bos_direction = None

    if recent_bos:

        bos_type = str(
            recent_bos.get(
                "type",
                ""
            )
        ).upper()

        if "BULLISH" in bos_type:

            recent_bos_direction = "BULLISH"

        elif "BEARISH" in bos_type:

            recent_bos_direction = "BEARISH"

    recent_choch_direction = None

    if recent_choch:

        choch_type = str(
            recent_choch.get(
                "type",
                ""
            )
        ).upper()

        if "BULLISH" in choch_type:

            recent_choch_direction = "BULLISH"

        elif "BEARISH" in choch_type:

            recent_choch_direction = "BEARISH"

    reasons = []

    if trend == "BULLISH":

        reasons.append(
            "4H market structure bullish"
        )

    elif trend == "BEARISH":

        reasons.append(
            "4H market structure bearish"
        )

    if recent_bos_direction:

        reasons.append(
            f"Latest 4H BOS: "
            f"{recent_bos_direction}"
        )

    if recent_choch_direction:

        reasons.append(
            f"Latest 4H CHOCH: "
            f"{recent_choch_direction}"
        )

    return {
        "direction": trend,
        "recent_bos": recent_bos,
        "recent_choch": recent_choch,
        "recent_bos_direction": recent_bos_direction,
        "recent_choch_direction": recent_choch_direction,
        "reasons": reasons,
    }


# ============================================================
# RETRACEMENT
# ============================================================

def detect_retracement(
    major_direction,
    structure_direction,
    h1_direction,
    m15_direction,
):

    # --------------------------------------------------------
    # BEARISH MARKET + BULLISH LOWER TIMEFRAME
    # --------------------------------------------------------

    if (
        major_direction == "BEARISH"
        and structure_direction == "BEARISH"
        and h1_direction == "BULLISH"
        and m15_direction == "BULLISH"
    ):

        return "BEARISH_RETRACEMENT"

    # --------------------------------------------------------
    # BULLISH MARKET + BEARISH LOWER TIMEFRAME
    # --------------------------------------------------------

    if (
        major_direction == "BULLISH"
        and structure_direction == "BULLISH"
        and h1_direction == "BEARISH"
        and m15_direction == "BEARISH"
    ):

        return "BULLISH_RETRACEMENT"

    return "NONE"


# ============================================================
# ENTRY TRIGGER
# ============================================================

def determine_entry_trigger(
    major_direction,
    structure_direction,
    h1_direction,
    m15_direction,
    structure_data,
):

    if (
        major_direction == "BEARISH"
        and structure_direction == "BEARISH"
        and h1_direction == "BEARISH"
        and m15_direction == "BEARISH"
    ):

        return "SELL_ALIGNMENT"

    if (
        major_direction == "BULLISH"
        and structure_direction == "BULLISH"
        and h1_direction == "BULLISH"
        and m15_direction == "BULLISH"
    ):

        return "BUY_ALIGNMENT"

    return "NO_TRIGGER"


# ============================================================
# LEVELS
# ============================================================

def get_levels(
    structure_data
):

    support = None
    resistance = None

    if not structure_data:

        return support, resistance

    supports = structure_data.get(
        "support",
        []
    )

    resistances = structure_data.get(
        "resistance",
        []
    )

    # Nearest support

    if supports:

        try:

            support = float(
                supports[0]["price"]
            )

        except (
            TypeError,
            ValueError,
            KeyError,
        ):

            pass

    # Nearest resistance

    if resistances:

        try:

            resistance = float(
                resistances[0]["price"]
            )

        except (
            TypeError,
            ValueError,
            KeyError,
        ):

            pass

    return support, resistance


# ============================================================
# LEVEL PROXIMITY
# ============================================================

def check_level_proximity(
    price,
    direction,
    support,
    resistance,
    atr,
):

    if not price or not atr:

        return {
            "blocked": False,
            "reason": None,
        }

    distance = (
        atr * LEVEL_PROXIMITY_ATR
    )

    # BUY near resistance

    if (
        direction == "BUY"
        and resistance is not None
    ):

        if (
            abs(
                resistance - price
            ) <= distance
        ):

            return {
                "blocked": True,
                "reason":
                    "BUY blocked: price too close to resistance",
            }

    # SELL near support

    if (
        direction == "SELL"
        and support is not None
    ):

        if (
            abs(
                price - support
            ) <= distance
        ):

            return {
                "blocked": True,
                "reason":
                    "SELL blocked: price too close to support",
            }

    return {
        "blocked": False,
        "reason": None,
    }


# ============================================================
# TRADE LEVELS
# ============================================================

def calculate_trade_levels(
    direction,
    price,
    atr,
    support,
    resistance,
):

    price = safe_float(
        price
    )

    atr = safe_float(
        atr
    )

    if not price or not atr:

        return {
            "entry": price,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "risk": None,
        }

    atr_risk = (
        atr * ATR_SL_MULTIPLIER
    )

    structure_buffer = (
        atr * STRUCTURE_BUFFER_ATR
    )

    # ========================================================
    # BUY
    # ========================================================

    if direction == "BUY":

        stop_loss = (
            price - atr_risk
        )

        if support:

            structure_sl = (
                support
                - structure_buffer
            )

            if (
                structure_sl < price
                and
                price - structure_sl
                <= atr_risk * 1.5
            ):

                stop_loss = structure_sl

        actual_risk = (
            price - stop_loss
        )

        tp1 = (
            price
            + actual_risk * RR_TP1
        )

        tp2 = (
            price
            + actual_risk * RR_TP2
        )

    # ========================================================
    # SELL
    # ========================================================

    elif direction == "SELL":

        stop_loss = (
            price + atr_risk
        )

        if resistance:

            structure_sl = (
                resistance
                + structure_buffer
            )

            if (
                structure_sl > price
                and
                structure_sl - price
                <= atr_risk * 1.5
            ):

                stop_loss = structure_sl

        actual_risk = (
            stop_loss - price
        )

        tp1 = (
            price
            - actual_risk * RR_TP1
        )

        tp2 = (
            price
            - actual_risk * RR_TP2
        )

    else:

        return {
            "entry": price,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "risk": None,
        }

    return {
        "entry": price,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "risk": actual_risk,
    }


# ============================================================
# MAIN
# ============================================================

def generate_signal(
    timeframe_data,
    structure_data,
):

    d1 = timeframe_data.get(
        "1d",
        {}
    )

    h4 = timeframe_data.get(
        "4h",
        {}
    )

    h1 = timeframe_data.get(
        "1h",
        {}
    )

    m15 = timeframe_data.get(
        "15m",
        {}
    )

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    major = determine_major_trend(
        d1
    )

    h4_indicators = (
        get_indicator_direction(
            h4
        )
    )

    h1_result = (
        get_indicator_direction(
            h1
        )
    )

    m15_result = (
        get_indicator_direction(
            m15
        )
    )

    structure = (
        determine_structure_direction(
            structure_data
        )
    )

    major_direction = (
        major["direction"]
    )

    structure_direction = (
        structure["direction"]
    )

    h1_direction = (
        h1_result["direction"]
    )

    m15_direction = (
        m15_result["direction"]
    )

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    price = safe_float(
        m15.get(
            "price",
            h1.get(
                "price",
                h4.get(
                    "price",
                    d1.get(
                        "price",
                        0
                    )
                )
            )
        )
    )

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

    atr = safe_float(
        m15.get(
            "ATR14",
            h1.get(
                "ATR14",
                h4.get(
                    "ATR14",
                    d1.get(
                        "ATR14",
                        0
                    )
                )
            )
        )
    )

    # --------------------------------------------------------
    # LEVELS
    # --------------------------------------------------------

    support, resistance = (
        get_levels(
            structure_data
        )
    )

    # --------------------------------------------------------
    # MARKET PHASE
    # --------------------------------------------------------

    market_phase = detect_retracement(
        major_direction,
        structure_direction,
        h1_direction,
        m15_direction,
    )

    # --------------------------------------------------------
    # ENTRY TRIGGER
    # --------------------------------------------------------

    entry_trigger = (
        determine_entry_trigger(
            major_direction,
            structure_direction,
            h1_direction,
            m15_direction,
            structure_data,
        )
    )

    # --------------------------------------------------------
    # ALIGNMENT
    # --------------------------------------------------------

    confirmations = 0

    alignment_reasons = []

    # 1D + 4H

    if (
        major_direction != "NEUTRAL"
        and
        major_direction == structure_direction
    ):

        confirmations += 1

        alignment_reasons.append(
            f"1D + 4H aligned: "
            f"{major_direction}"
        )

    # 1H

    if (
        h1_direction != "NEUTRAL"
        and
        h1_direction == major_direction
    ):

        confirmations += 1

        alignment_reasons.append(
            f"1H confirms: "
            f"{major_direction}"
        )

    # 15M

    if (
        m15_direction != "NEUTRAL"
        and
        m15_direction == major_direction
    ):

        confirmations += 1

        alignment_reasons.append(
            f"15M confirms: "
            f"{major_direction}"
        )

    # --------------------------------------------------------
    # SIGNAL
    # --------------------------------------------------------

    signal = "WAIT"

    reasons = []

    reasons.extend(
        alignment_reasons
    )

    reasons.extend(
        structure["reasons"]
    )

    # ========================================================
    # BUY
    # ========================================================

    if (
        major_direction == "BULLISH"
        and
        structure_direction == "BULLISH"
        and
        h1_direction == "BULLISH"
        and
        m15_direction == "BULLISH"
        and
        entry_trigger == "BUY_ALIGNMENT"
        and
        confirmations >= MIN_CONFIRMATIONS
    ):

        signal = "BUY"

    # ========================================================
    # SELL
    # ========================================================

    elif (
        major_direction == "BEARISH"
        and
        structure_direction == "BEARISH"
        and
        h1_direction == "BEARISH"
        and
        m15_direction == "BEARISH"
        and
        entry_trigger == "SELL_ALIGNMENT"
        and
        confirmations >= MIN_CONFIRMATIONS
    ):

        signal = "SELL"

    # ========================================================
    # RETRACEMENT
    # ========================================================

    if market_phase == "BEARISH_RETRACEMENT":

        reasons.append(
            "1H + 15M bullish against bearish higher timeframe"
        )

        reasons.append(
            "Possible bearish-market retracement"
        )

        reasons.append(
            "Waiting for bearish 15M confirmation"
        )

    elif market_phase == "BULLISH_RETRACEMENT":

        reasons.append(
            "1H + 15M bearish against bullish higher timeframe"
        )

        reasons.append(
            "Possible bullish-market retracement"
        )

        reasons.append(
            "Waiting for bullish 15M confirmation"
        )

    # ========================================================
    # NEUTRAL / CONFLICT
    # ========================================================

    if (
        major_direction == "NEUTRAL"
    ):

        reasons.append(
            "1D major trend is neutral"
        )

    if (
        h1_direction == "NEUTRAL"
    ):

        reasons.append(
            "1H confirmation is neutral"
        )

    if (
        m15_direction == "NEUTRAL"
    ):

        reasons.append(
            "15M entry direction is neutral"
        )

    # ========================================================
    # LEVEL PROTECTION
    # ========================================================

    level_check = (
        check_level_proximity(
            price=price,
            direction=signal,
            support=support,
            resistance=resistance,
            atr=atr,
        )
    )

    if (
        signal in (
            "BUY",
            "SELL"
        )
        and
        level_check["blocked"]
    ):

        signal = "WAIT"

        reasons.append(
            level_check["reason"]
        )

    # ========================================================
    # TRADE LEVELS
    # ========================================================

    if signal in (
        "BUY",
        "SELL"
    ):

        trade = (
            calculate_trade_levels(
                direction=signal,
                price=price,
                atr=atr,
                support=support,
                resistance=resistance,
            )
        )

    else:

        trade = {
            "entry": price,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "risk": None,
        }

    # ========================================================
    # TECHNICAL ALIGNMENT
    # ========================================================

    alignment_score = (
        confirmations * 25
    )

    # Extra structure BOS confirmation

    if (
        structure[
            "recent_bos_direction"
        ]
        == major_direction
    ):

        alignment_score += 10

    # CHOCH in major direction

    if (
        structure[
            "recent_choch_direction"
        ]
        == major_direction
    ):

        alignment_score += 10

    if alignment_score > 100:

        alignment_score = 100

    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {

        "signal": signal,

        "price": price,

        "confidence": alignment_score,

        "confirmations": confirmations,

        "major_direction":
            major_direction,

        "structure_direction":
            structure_direction,

        "h1_direction":
            h1_direction,

        "m15_direction":
            m15_direction,

        "market_phase":
            market_phase,

        "entry_trigger":
            entry_trigger,

        "entry":
            trade["entry"],

        "stop_loss":
            trade["stop_loss"],

        "tp1":
            trade["tp1"],

        "tp2":
            trade["tp2"],

        "risk":
            trade["risk"],

        "support":
            support,

        "resistance":
            resistance,

        "recent_bos":
            structure[
                "recent_bos"
            ],

        "recent_choch":
            structure[
                "recent_choch"
            ],

        "reasons":
            reasons,
    }


# ============================================================
# FORMAT
# ============================================================

def format_signal(
    result
):

    signal = result.get(
        "signal",
        "WAIT"
    )

    price = safe_float(
        result.get(
            "price"
        )
    )

    confidence = safe_float(
        result.get(
            "confidence"
        )
    )

    confirmations = result.get(
        "confirmations",
        0
    )

    major = result.get(
        "major_direction",
        "NEUTRAL"
    )

    structure = result.get(
        "structure_direction",
        "NEUTRAL"
    )

    h1 = result.get(
        "h1_direction",
        "NEUTRAL"
    )

    m15 = result.get(
        "m15_direction",
        "NEUTRAL"
    )

    phase = result.get(
        "market_phase",
        "NONE"
    )

    trigger = result.get(
        "entry_trigger",
        "NO_TRIGGER"
    )

    entry = result.get(
        "entry"
    )

    sl = result.get(
        "stop_loss"
    )

    tp1 = result.get(
        "tp1"
    )

    tp2 = result.get(
        "tp2"
    )

    risk = result.get(
        "risk"
    )

    support = result.get(
        "support"
    )

    resistance = result.get(
        "resistance"
    )

    lines = []

    lines.append(
        "XAU/USD SIGNAL V3.1"
    )

    lines.append(
        "=" * 30
    )

    lines.append(
        f"SIGNAL: {signal}"
    )

    lines.append(
        f"PRICE: {price:.3f}"
    )

    lines.append(
        f"CONFIRMATIONS: "
        f"{confirmations}/3"
    )

    lines.append(
        f"TECHNICAL ALIGNMENT: "
        f"{confidence:.1f}%"
    )

    lines.append("")

    lines.append(
        "TIMEFRAME ANALYSIS"
    )

    lines.append(
        f"1D  : {major}"
    )

    lines.append(
        f"4H  : {structure}"
    )

    lines.append(
        f"1H  : {h1}"
    )

    lines.append(
        f"15M : {m15}"
    )

    lines.append("")

    lines.append(
        f"MARKET PHASE: {phase}"
    )

    lines.append(
        f"ENTRY TRIGGER: {trigger}"
    )

    lines.append("")

    if signal in (
        "BUY",
        "SELL"
    ):

        lines.append(
            "TRADE SETUP"
        )

        lines.append(
            f"ENTRY: {entry:.3f}"
        )

        lines.append(
            f"STOP LOSS: {safe_float(sl):.3f}"
        )

        lines.append(
            f"TP1: {safe_float(tp1):.3f}"
        )

        lines.append(
            f"TP2: {safe_float(tp2):.3f}"
        )

        lines.append(
            f"RISK: {safe_float(risk):.3f}"
        )

    else:

        lines.append(
            "TRADE SETUP: WAIT"
        )

        lines.append(
            "No confirmed entry."
        )

    lines.append("")

    if support is not None:

        lines.append(
            f"SUPPORT: "
            f"{support:.3f}"
        )

    if resistance is not None:

        lines.append(
            f"RESISTANCE: "
            f"{resistance:.3f}"
        )

    lines.append("")

    lines.append(
        "REASONS"
    )

    lines.append(
        "-" * 30
    )

    # Remove duplicate reasons

    seen = set()

    for reason in result.get(
        "reasons",
        []
    ):

        if reason in seen:
            continue

        seen.add(reason)

        lines.append(
            f"- {reason}"
        )

    return "\n".join(
        lines
    )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Signal Engine V3.1 loaded successfully."
    )
