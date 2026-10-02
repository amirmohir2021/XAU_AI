"""
XAU_AI Strategy Analyzer V3
===========================

Purpose:
    Historical no-lookahead analysis using the REAL XAU_AI V3.1
    signal engine.

Architecture:

    Historical 5M candle
            |
            +--> Liquidity Sweep / 5M analysis
            |
            +--> Historical 15M
            +--> Historical 1H
            +--> Historical 4H
            +--> Historical 1D
            |
            +--> REAL signal_engine.generate_signal()
            |
            +--> Historical trade levels
            |
            +--> Future 5M candles
                    |
                    +--> WIN / LOSS / OPEN

IMPORTANT:
    This file is for research/backtesting only.

    It does NOT modify:
        analysis.signal_engine
        analysis.scalping_5m
        analysis.structure
        strategies

    It does NOT use future candles for signal generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from data.market_data import get_xauusd_candles

from analysis.scalping_5m import analyze_5m
from analysis.scalping_levels import generate_scalping_levels
from analysis.signal_engine import generate_signal


# ============================================================
# SETTINGS
# ============================================================

TIMEFRAME_5M = "5m"
TIMEFRAME_15M = "15m"
TIMEFRAME_1H = "1h"
TIMEFRAME_4H = "4h"
TIMEFRAME_1D = "1d"

CANDLE_LIMIT_5M = 1000
CANDLE_LIMIT_HTF = 1000

MIN_CANDLES_5M = 220
MIN_CANDLES_HTF = 50


# ============================================================
# DATA CLASS
# ============================================================

@dataclass
class AnalyzerTrade:

    time: Any

    direction: str
    sweep_type: str
    setup: str

    entry: float
    stop_loss: float
    tp1: float
    risk: float

    result: str
    result_r: float

    # --------------------------------------------------------
    # 5M
    # --------------------------------------------------------

    rsi: Optional[float] = None
    adx: Optional[float] = None
    atr: Optional[float] = None

    strength: Optional[str] = None

    trend_5m: str = "UNKNOWN"
    structure_5m: str = "UNKNOWN"

    # --------------------------------------------------------
    # Real V3.1
    # --------------------------------------------------------

    v31_signal: str = "UNKNOWN"
    v31_alignment: Optional[float] = None
    confirmations: int = 0

    major_direction: str = "UNKNOWN"
    structure_direction: str = "UNKNOWN"
    h1_direction: str = "UNKNOWN"
    m15_direction: str = "UNKNOWN"

    market_phase: str = "UNKNOWN"
    entry_trigger: str = "UNKNOWN"

    # --------------------------------------------------------
    # HTF indicators
    # --------------------------------------------------------

    trend_1d: str = "UNKNOWN"
    trend_4h: str = "UNKNOWN"
    trend_1h: str = "UNKNOWN"
    trend_15m: str = "UNKNOWN"

    htf_agreement: str = "UNKNOWN"

    # --------------------------------------------------------
    # Indicator directions
    # --------------------------------------------------------

    ema_direction: str = "UNKNOWN"
    macd_direction: str = "UNKNOWN"
    dmi_direction: str = "UNKNOWN"


# ============================================================
# SAFE HELPERS
# ============================================================

def safe_float(
    value: Any,
    default: Optional[float] = None,
) -> Optional[float]:

    try:

        if value is None:
            return default

        value = float(value)

        if pd.isna(value):
            return default

        return value

    except (
        TypeError,
        ValueError,
    ):

        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):

        return default


def safe_str(
    value: Any,
    default: str = "UNKNOWN",
) -> str:

    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    return value.upper()


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()

    if "openTime" not in result.columns:
        return pd.DataFrame()

    result["openTime"] = pd.to_datetime(
        result["openTime"],
        utc=True,
        errors="coerce",
    )

    result = result.dropna(
        subset=["openTime"]
    )

    # Never use currently open candle.
    if "isOpen" in result.columns:

        result = result[
            result["isOpen"] == False
        ].copy()

    result = result.sort_values(
        "openTime"
    ).reset_index(
        drop=True
    )

    return result


# ============================================================
# HISTORICAL DATA AVAILABLE AT SIGNAL TIME
# ============================================================

def historical_slice(
    df: pd.DataFrame,
    signal_time: pd.Timestamp,
) -> pd.DataFrame:

    if df.empty:
        return df

    return df[
        df["openTime"] <= signal_time
    ].copy().reset_index(
        drop=True
    )


# ============================================================
# INDICATOR CALCULATION
#
# This intentionally reproduces the same indicator field
# names expected by analysis.signal_engine.
# ============================================================

def calculate_indicators(
    df: pd.DataFrame,
) -> Dict[str, Any]:

    if df.empty:
        return {}

    if len(df) < 30:
        return {}

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    # --------------------------------------------------------
    # EMA
    # --------------------------------------------------------

    ema20_series = close.ewm(
        span=20,
        adjust=False,
    ).mean()

    ema50_series = close.ewm(
        span=50,
        adjust=False,
    ).mean()

    ema200_series = close.ewm(
        span=200,
        adjust=False,
    ).mean()

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    delta = close.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False,
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        pd.NA,
    )

    rsi_series = (
        100
        - (
            100
            / (1 + rs)
        )
    )

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    ema12 = close.ewm(
        span=12,
        adjust=False,
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False,
    ).mean()

    macd_series = (
        ema12 - ema26
    )

    macd_signal_series = (
        macd_series.ewm(
            span=9,
            adjust=False,
        ).mean()
    )

    macd_hist_series = (
        macd_series
        - macd_signal_series
    )

    # --------------------------------------------------------
    # ATR
    # --------------------------------------------------------

    previous_close = close.shift(1)

    tr1 = high - low

    tr2 = (
        high
        - previous_close
    ).abs()

    tr3 = (
        low
        - previous_close
    ).abs()

    true_range = pd.concat(
        [
            tr1,
            tr2,
            tr3,
        ],
        axis=1,
    ).max(
        axis=1
    )

    atr_series = (
        true_range
        .rolling(14)
        .mean()
    )

    # --------------------------------------------------------
    # DMI / ADX
    # --------------------------------------------------------

    up_move = (
        high.diff()
    )

    down_move = (
        -low.diff()
    )

    plus_dm = up_move.where(
        (
            up_move > down_move
        )
        & (
            up_move > 0
        ),
        0.0,
    )

    minus_dm = down_move.where(
        (
            down_move > up_move
        )
        & (
            down_move > 0
        ),
        0.0,
    )

    atr14 = atr_series

    di_plus_series = (
        100
        * plus_dm.rolling(14).mean()
        / atr14.replace(0, pd.NA)
    )

    di_minus_series = (
        100
        * minus_dm.rolling(14).mean()
        / atr14.replace(0, pd.NA)
    )

    di_sum = (
        di_plus_series
        + di_minus_series
    )

    dx = (
        100
        * (
            (
                di_plus_series
                - di_minus_series
            ).abs()
            / di_sum.replace(
                0,
                pd.NA,
            )
        )
    )

    adx_series = (
        dx.rolling(14)
        .mean()
    )

    # --------------------------------------------------------
    # Bollinger Bands
    # --------------------------------------------------------

    bb_mid = (
        close.rolling(20)
        .mean()
    )

    bb_std = (
        close.rolling(20)
        .std()
    )

    bb_high = (
        bb_mid
        + 2 * bb_std
    )

    bb_low = (
        bb_mid
        - 2 * bb_std
    )

    # --------------------------------------------------------
    # Stochastic
    # --------------------------------------------------------

    lowest_low = (
        low.rolling(14)
        .min()
    )

    highest_high = (
        high.rolling(14)
        .max()
    )

    denominator = (
        highest_high
        - lowest_low
    )

    stoch_k = (
        100
        * (
            close
            - lowest_low
        )
        / denominator.replace(
            0,
            pd.NA,
        )
    )

    # --------------------------------------------------------
    # Latest values
    # --------------------------------------------------------

    def latest(series):
        return safe_float(
            series.iloc[-1]
        )

    return {
        "price": latest(close),

        "EMA20": latest(
            ema20_series
        ),

        "EMA50": latest(
            ema50_series
        ),

        "EMA200": latest(
            ema200_series
        ),

        "RSI14": latest(
            rsi_series
        ),

        "MACD": latest(
            macd_series
        ),

        "MACD_SIGNAL": latest(
            macd_signal_series
        ),

        "MACD_HIST": latest(
            macd_hist_series
        ),

        "ATR14": latest(
            atr_series
        ),

        "ADX14": latest(
            adx_series
        ),

        "DI_PLUS": latest(
            di_plus_series
        ),

        "DI_MINUS": latest(
            di_minus_series
        ),

        "BB_HIGH": latest(
            bb_high
        ),

        "BB_MID": latest(
            bb_mid
        ),

        "BB_LOW": latest(
            bb_low
        ),

        "STOCH_K": latest(
            stoch_k
        ),
    }


# ============================================================
# INDICATOR DIRECTION
#
# Uses the same scoring logic as signal_engine.py.
# ============================================================

def calculate_indicator_direction(
    indicators: Dict[str, Any],
) -> Dict[str, Any]:

    if not indicators:
        return {
            "direction": "UNKNOWN",
            "bullish_score": 0,
            "bearish_score": 0,
            "strength": "UNKNOWN",
        }

    bullish = 0
    bearish = 0

    price = safe_float(
        indicators.get("price"),
        0.0,
    )

    ema20 = safe_float(
        indicators.get("EMA20"),
        0.0,
    )

    ema50 = safe_float(
        indicators.get("EMA50"),
        0.0,
    )

    ema200 = safe_float(
        indicators.get("EMA200"),
        0.0,
    )

    rsi = safe_float(
        indicators.get("RSI14"),
        0.0,
    )

    macd = safe_float(
        indicators.get("MACD"),
        0.0,
    )

    macd_signal = safe_float(
        indicators.get("MACD_SIGNAL"),
        0.0,
    )

    di_plus = safe_float(
        indicators.get("DI_PLUS"),
        0.0,
    )

    di_minus = safe_float(
        indicators.get("DI_MINUS"),
        0.0,
    )

    adx = safe_float(
        indicators.get("ADX14"),
        0.0,
    )

    # Price / EMA20

    if price and ema20:

        if price > ema20:
            bullish += 2

        elif price < ema20:
            bearish += 2

    # EMA20 / EMA50

    if ema20 and ema50:

        if ema20 > ema50:
            bullish += 2

        elif ema20 < ema50:
            bearish += 2

    # Price / EMA200

    if price and ema200:

        if price > ema200:
            bullish += 1

        elif price < ema200:
            bearish += 1

    # RSI

    if rsi:

        if rsi >= 55:
            bullish += 2

        elif rsi <= 45:
            bearish += 2

    # MACD

    if macd or macd_signal:

        if macd > macd_signal:
            bullish += 1

        elif macd < macd_signal:
            bearish += 1

    # DMI

    if di_plus or di_minus:

        if di_plus > di_minus:
            bullish += 1

        elif di_minus > di_plus:
            bearish += 1

    # Direction

    if (
        bullish > bearish
        and bullish >= 5
    ):

        direction = "BULLISH"

    elif (
        bearish > bullish
        and bearish >= 5
    ):

        direction = "BEARISH"

    else:

        direction = "NEUTRAL"

    # Strength

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
    }


# ============================================================
# HTF AGREEMENT
# ============================================================

def determine_htf_agreement(
    trends: Dict[str, str],
) -> str:

    values = [
        trends.get("1d", "UNKNOWN"),
        trends.get("4h", "UNKNOWN"),
        trends.get("1h", "UNKNOWN"),
        trends.get("15m", "UNKNOWN"),
    ]

    bullish = values.count(
        "BULLISH"
    )

    bearish = values.count(
        "BEARISH"
    )

    if bullish >= 3:
        return "BULLISH"

    if bearish >= 3:
        return "BEARISH"

    if bullish > bearish:
        return "WEAK_BULLISH"

    if bearish > bullish:
        return "WEAK_BEARISH"

    return "MIXED"


# ============================================================
# STRUCTURE DATA
#
# We intentionally keep structure generation isolated.
# The existing V3.1 engine receives this structure object.
# ============================================================

def build_structure_data(
    df_4h: pd.DataFrame,
) -> Dict[str, Any]:

    """
    Build 4H structure using the existing structure module.

    Multiple possible public function names are supported so
    this analyzer remains compatible with the existing project
    implementation.
    """

    if df_4h.empty:
        return {}

    try:

        import analysis.structure as structure_module

    except Exception:

        return {}

    candidate_names = [
        "analyze_structure",
        "get_market_structure",
        "detect_structure",
        "calculate_structure",
    ]

    for name in candidate_names:

        function = getattr(
            structure_module,
            name,
            None,
        )

        if not callable(function):
            continue

        try:

            result = function(
                df_4h
            )

            if isinstance(
                result,
                dict,
            ):

                return result

        except TypeError:

            continue

        except Exception:

            continue

    return {}


# ============================================================
# V3.1 CONTEXT
# ============================================================

def build_v31_context(
    history_5m: pd.DataFrame,
    history_15m: pd.DataFrame,
    history_1h: pd.DataFrame,
    history_4h: pd.DataFrame,
    history_1d: pd.DataFrame,
) -> Optional[Dict[str, Any]]:

    if (
        history_15m.empty
        or history_1h.empty
        or history_4h.empty
        or history_1d.empty
    ):
        return None

    # --------------------------------------------------------
    # Indicators
    # --------------------------------------------------------

    indicators_1d = calculate_indicators(
        history_1d
    )

    indicators_4h = calculate_indicators(
        history_4h
    )

    indicators_1h = calculate_indicators(
        history_1h
    )

    indicators_15m = calculate_indicators(
        history_15m
    )

    if not indicators_1d:
        return None

    if not indicators_4h:
        return None

    if not indicators_1h:
        return None

    if not indicators_15m:
        return None

    timeframe_data = {
        "1d": indicators_1d,
        "4h": indicators_4h,
        "1h": indicators_1h,
        "15m": indicators_15m,
    }

    # --------------------------------------------------------
    # Existing 4H structure engine
    # --------------------------------------------------------

    structure_data = build_structure_data(
        history_4h
    )

    # --------------------------------------------------------
    # REAL V3.1 SIGNAL ENGINE
    # --------------------------------------------------------

    try:

        result = generate_signal(
            timeframe_data,
            structure_data,
        )

    except Exception as exc:

        return {
            "error": str(exc),
            "timeframe_data": timeframe_data,
            "structure_data": structure_data,
        }

    if not isinstance(
        result,
        dict,
    ):
        return None

    # --------------------------------------------------------
    # Trends
    # --------------------------------------------------------

    trend_1d = safe_str(
        result.get(
            "major_direction",
            calculate_indicator_direction(
                indicators_1d
            )["direction"],
        )
    )

    trend_4h = safe_str(
        result.get(
            "structure_direction",
            calculate_indicator_direction(
                indicators_4h
            )["direction"],
        )
    )

    trend_1h = safe_str(
        result.get(
            "h1_direction",
            calculate_indicator_direction(
                indicators_1h
            )["direction"],
        )
    )

    trend_15m = safe_str(
        result.get(
            "m15_direction",
            calculate_indicator_direction(
                indicators_15m
            )["direction"],
        )
    )

    trends = {
        "1d": trend_1d,
        "4h": trend_4h,
        "1h": trend_1h,
        "15m": trend_15m,
    }

    # --------------------------------------------------------
    # 5M
    # --------------------------------------------------------

    try:

        analysis_5m = analyze_5m(
            history_5m
        )

    except Exception:

        analysis_5m = {}

    trend_5m = "UNKNOWN"

    structure_5m = "UNKNOWN"

    rsi_5m = None
    adx_5m = None
    atr_5m = None
    strength_5m = None

    ema_direction = "UNKNOWN"
    macd_direction = "UNKNOWN"
    dmi_direction = "UNKNOWN"

    if isinstance(
        analysis_5m,
        dict,
    ):

        trend_5m = safe_str(
            analysis_5m.get(
                "direction",
                "UNKNOWN",
            )
        )

        structure_5m = safe_str(
            analysis_5m.get(
                "structure",
                "UNKNOWN",
            )
        )

        rsi_5m = safe_float(
            analysis_5m.get(
                "rsi"
            )
        )

        adx_5m = safe_float(
            analysis_5m.get(
                "adx"
            )
        )

        atr_5m = safe_float(
            analysis_5m.get(
                "atr"
            )
        )

        strength_5m = (
            analysis_5m.get(
                "strength"
            )
        )

    # Use the exact V3.1 indicator direction logic
    # for 5M feature reporting.

    indicators_5m = calculate_indicators(
        history_5m
    )

    direction_5m = calculate_indicator_direction(
        indicators_5m
    )

    if direction_5m:

        ema20 = safe_float(
            indicators_5m.get(
                "EMA20"
            )
        )

        ema50 = safe_float(
            indicators_5m.get(
                "EMA50"
            )
        )

        macd = safe_float(
            indicators_5m.get(
                "MACD"
            )
        )

        macd_signal = safe_float(
            indicators_5m.get(
                "MACD_SIGNAL"
            )
        )

        di_plus = safe_float(
            indicators_5m.get(
                "DI_PLUS"
            )
        )

        di_minus = safe_float(
            indicators_5m.get(
                "DI_MINUS"
            )
        )

        if (
            ema20 is not None
            and ema50 is not None
        ):

            if ema20 > ema50:
                ema_direction = "BULLISH"

            elif ema20 < ema50:
                ema_direction = "BEARISH"

            else:
                ema_direction = "NEUTRAL"

        if (
            macd is not None
            and macd_signal is not None
        ):

            if macd > macd_signal:
                macd_direction = "BULLISH"

            elif macd < macd_signal:
                macd_direction = "BEARISH"

            else:
                macd_direction = "NEUTRAL"

        if (
            di_plus is not None
            and di_minus is not None
        ):

            if di_plus > di_minus:
                dmi_direction = "BULLISH"

            elif di_plus < di_minus:
                dmi_direction = "BEARISH"

            else:
                dmi_direction = "NEUTRAL"

    return {
        "result": result,

        "timeframe_data": timeframe_data,
        "structure_data": structure_data,

        "trend_1d": trend_1d,
        "trend_4h": trend_4h,
        "trend_1h": trend_1h,
        "trend_15m": trend_15m,
        "trend_5m": trend_5m,

        "htf_agreement": determine_htf_agreement(
            trends
        ),

        "rsi_5m": rsi_5m,
        "adx_5m": adx_5m,
        "atr_5m": atr_5m,
        "strength_5m": strength_5m,

        "ema_direction": ema_direction,
        "macd_direction": macd_direction,
        "dmi_direction": dmi_direction,

        "analysis_5m": analysis_5m,
    }


# ============================================================
# TRADE LEVELS
# ============================================================

def build_trade_from_setup(
    history_5m: pd.DataFrame,
    context: Dict[str, Any],
) -> Optional[AnalyzerTrade]:

    analysis_5m = context.get(
        "analysis_5m"
    )

    if not isinstance(
        analysis_5m,
        dict,
    ):
        return None

    sweep_type = safe_str(
        analysis_5m.get(
            "liquidity_sweep",
            "NONE",
        )
    )

    if sweep_type not in (
        "BULLISH_SWEEP",
        "BEARISH_SWEEP",
    ):
        return None

    try:

        levels = generate_scalping_levels(
            history_5m,
            analysis_5m,
        )

    except Exception:

        return None

    if not isinstance(
        levels,
        dict,
    ):
        return None

    if levels.get(
        "status"
    ) != "READY":

        return None

    direction = safe_str(
        levels.get(
            "direction",
            "",
        ),
        "",
    )

    if direction not in (
        "BUY",
        "SELL",
    ):
        return None

    entry = safe_float(
        levels.get(
            "entry"
        )
    )

    stop_loss = safe_float(
        levels.get(
            "stop_loss"
        )
    )

    tp1 = safe_float(
        levels.get(
            "tp1"
        )
    )

    if (
        entry is None
        or stop_loss is None
        or tp1 is None
    ):
        return None

    risk = abs(
        entry - stop_loss
    )

    if risk <= 0:
        return None

    result = context.get(
        "result"
    )

    if not isinstance(
        result,
        dict,
    ):
        return None

    signal_time = pd.Timestamp(
        history_5m.iloc[-1][
            "openTime"
        ]
    )

    return AnalyzerTrade(

        time=signal_time,

        direction=direction,

        sweep_type=sweep_type,

        setup=sweep_type,

        entry=entry,

        stop_loss=stop_loss,

        tp1=tp1,

        risk=risk,

        result="OPEN",

        result_r=0.0,

        rsi=context.get(
            "rsi_5m"
        ),

        adx=context.get(
            "adx_5m"
        ),

        atr=context.get(
            "atr_5m"
        ),

        strength=context.get(
            "strength_5m"
        ),

        trend_5m=context.get(
            "trend_5m",
            "UNKNOWN",
        ),

        structure_5m=safe_str(
            context.get(
                "analysis_5m",
                {},
            ).get(
                "structure",
                "UNKNOWN",
            )
        ),

        v31_signal=safe_str(
            result.get(
                "signal",
                "UNKNOWN",
            )
        ),

        v31_alignment=safe_float(
            result.get(
                "confidence"
            )
        ),

        confirmations=safe_int(
            result.get(
                "confirmations",
                0,
            )
        ),

        major_direction=safe_str(
            result.get(
                "major_direction",
                "UNKNOWN",
            )
        ),

        structure_direction=safe_str(
            result.get(
                "structure_direction",
                "UNKNOWN",
            )
        ),

        h1_direction=safe_str(
            result.get(
                "h1_direction",
                "UNKNOWN",
            )
        ),

        m15_direction=safe_str(
            result.get(
                "m15_direction",
                "UNKNOWN",
            )
        ),

        market_phase=safe_str(
            result.get(
                "market_phase",
                "UNKNOWN",
            )
        ),

        entry_trigger=safe_str(
            result.get(
                "entry_trigger",
                "UNKNOWN",
            )
        ),

        trend_1d=context.get(
            "trend_1d",
            "UNKNOWN",
        ),

        trend_4h=context.get(
            "trend_4h",
            "UNKNOWN",
        ),

        trend_1h=context.get(
            "trend_1h",
            "UNKNOWN",
        ),

        trend_15m=context.get(
            "trend_15m",
            "UNKNOWN",
        ),

        htf_agreement=context.get(
            "htf_agreement",
            "UNKNOWN",
        ),

        ema_direction=context.get(
            "ema_direction",
            "UNKNOWN",
        ),

        macd_direction=context.get(
            "macd_direction",
            "UNKNOWN",
        ),

        dmi_direction=context.get(
            "dmi_direction",
            "UNKNOWN",
        ),
    )


# ============================================================
# OUTCOME
# ============================================================

def check_trade_outcome(
    future_df: pd.DataFrame,
    direction: str,
    entry: float,
    stop_loss: float,
    tp1: float,
) -> Tuple[str, float]:

    if future_df.empty:
        return "OPEN", 0.0

    risk = abs(
        entry - stop_loss
    )

    if risk <= 0:
        return "OPEN", 0.0

    direction = direction.upper()

    for _, candle in future_df.iterrows():

        high = safe_float(
            candle.get("high")
        )

        low = safe_float(
            candle.get("low")
        )

        if high is None or low is None:
            continue

        # ----------------------------------------------------
        # BUY
        # ----------------------------------------------------

        if direction == "BUY":

            stop_hit = (
                low <= stop_loss
            )

            tp_hit = (
                high >= tp1
            )

            # Conservative:
            # same candle = SL first.
            if stop_hit and tp_hit:
                return "LOSS", -1.0

            if stop_hit:
                return "LOSS", -1.0

            if tp_hit:

                reward = abs(
                    tp1 - entry
                )

                return (
                    "WIN",
                    reward / risk,
                )

        # ----------------------------------------------------
        # SELL
        # ----------------------------------------------------

        elif direction == "SELL":

            stop_hit = (
                high >= stop_loss
            )

            tp_hit = (
                low <= tp1
            )

            if stop_hit and tp_hit:
                return "LOSS", -1.0

            if stop_hit:
                return "LOSS", -1.0

            if tp_hit:

                reward = abs(
                    entry - tp1
                )

                return (
                    "WIN",
                    reward / risk,
                )

    return "OPEN", 0.0


# ============================================================
# RUN BACKTEST
# ============================================================

def run_analysis(
    df_5m: pd.DataFrame,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame,
    df_1d: pd.DataFrame,
) -> List[AnalyzerTrade]:

    trades: List[
        AnalyzerTrade
    ] = []

    if len(df_5m) < MIN_CANDLES_5M:
        return trades

    for i in range(
        MIN_CANDLES_5M - 1,
        len(df_5m),
    ):

        history_5m = df_5m.iloc[
            : i + 1
        ].copy()

        signal_time = pd.Timestamp(
            history_5m.iloc[-1][
                "openTime"
            ]
        )

        # ----------------------------------------------------
        # CRITICAL:
        # Each HTF dataframe is cut at signal time.
        # No future HTF candle is visible.
        # ----------------------------------------------------

        history_15m = historical_slice(
            df_15m,
            signal_time,
        )

        history_1h = historical_slice(
            df_1h,
            signal_time,
        )

        history_4h = historical_slice(
            df_4h,
            signal_time,
        )

        history_1d = historical_slice(
            df_1d,
            signal_time,
        )

        if (
            len(history_15m)
            < MIN_CANDLES_HTF
        ):
            continue

        if (
            len(history_1h)
            < MIN_CANDLES_HTF
        ):
            continue

        if (
            len(history_4h)
            < MIN_CANDLES_HTF
        ):
            continue

        if (
            len(history_1d)
            < MIN_CANDLES_HTF
        ):
            continue

        # ----------------------------------------------------
        # Build REAL V3.1 context
        # ----------------------------------------------------

        context = build_v31_context(
            history_5m=history_5m,
            history_15m=history_15m,
            history_1h=history_1h,
            history_4h=history_4h,
            history_1d=history_1d,
        )

        if not context:
            continue

        if context.get(
            "error"
        ):
            continue

        # ----------------------------------------------------
        # Build liquidity sweep setup
        # ----------------------------------------------------

        trade = build_trade_from_setup(
            history_5m,
            context,
        )

        if trade is None:
            continue

        # ----------------------------------------------------
        # Future candles ONLY for outcome
        # ----------------------------------------------------

        future_5m = df_5m[
            df_5m["openTime"]
            > signal_time
        ].copy()

        result, result_r = (
            check_trade_outcome(
                future_df=future_5m,
                direction=trade.direction,
                entry=trade.entry,
                stop_loss=trade.stop_loss,
                tp1=trade.tp1,
            )
        )

        trade.result = result
        trade.result_r = result_r

        trades.append(
            trade
        )

    return trades


# ============================================================
# STATISTICS
# ============================================================

def calculate_statistics(
    trades: List[AnalyzerTrade],
) -> Dict[str, Any]:

    total = len(trades)

    wins = sum(
        1
        for trade in trades
        if trade.result == "WIN"
    )

    losses = sum(
        1
        for trade in trades
        if trade.result == "LOSS"
    )

    open_trades = sum(
        1
        for trade in trades
        if trade.result == "OPEN"
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
        trade.result_r
        for trade in trades
    )

    average_r = (
        total_r / total
        if total > 0
        else 0.0
    )

    gross_profit = sum(
        trade.result_r
        for trade in trades
        if trade.result_r > 0
    )

    gross_loss = abs(
        sum(
            trade.result_r
            for trade in trades
            if trade.result_r < 0
        )
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else 0.0
    )

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

    for trade in trades:

        equity += trade.result_r

        peak = max(
            peak,
            equity,
        )

        drawdown = (
            peak - equity
        )

        max_drawdown = max(
            max_drawdown,
            drawdown,
        )

    return {
        "total": total,
        "closed": closed,
        "open": open_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_r": total_r,
        "average_r": average_r,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
    }


# ============================================================
# GROUP STATISTICS
# ============================================================

def group_statistics(
    trades: List[AnalyzerTrade],
    attribute: str,
) -> List[Dict[str, Any]]:

    groups: Dict[
        str,
        List[AnalyzerTrade],
    ] = {}

    for trade in trades:

        value = getattr(
            trade,
            attribute,
            "UNKNOWN",
        )

        if value is None:
            value = "UNKNOWN"

        key = str(value)

        groups.setdefault(
            key,
            [],
        ).append(trade)

    rows = []

    for key, group in groups.items():

        stats = calculate_statistics(
            group
        )

        rows.append(
            {
                "group": key,
                **stats,
            }
        )

    rows.sort(
        key=lambda row: row["total"],
        reverse=True,
    )

    return rows


# ============================================================
# PRINT CATEGORY
# ============================================================

def print_category_statistics(
    trades: List[AnalyzerTrade],
    title: str,
    attribute: str,
) -> None:

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    rows = group_statistics(
        trades,
        attribute,
    )

    print(
        f"{'GROUP':<26}"
        f"{'TRADES':>8}"
        f"{'WINS':>7}"
        f"{'LOSS':>7}"
        f"{'WR %':>9}"
        f"{'TOTAL R':>11}"
        f"{'AVG R':>9}"
    )

    print("-" * 70)

    for row in rows:

        print(
            f"{row['group']:<26}"
            f"{row['total']:>8}"
            f"{row['wins']:>7}"
            f"{row['losses']:>7}"
            f"{row['win_rate']:>9.2f}"
            f"{row['total_r']:>11.2f}"
            f"{row['average_r']:>9.3f}"
        )


# ============================================================
# NUMERIC BUCKETS
# ============================================================

def bucket_value(
    value: Optional[float],
    ranges: List[
        Tuple[
            float,
            float,
            str,
        ]
    ],
) -> str:

    if value is None:
        return "UNKNOWN"

    for low, high, label in ranges:

        if (
            low
            <= value
            < high
        ):
            return label

    return "UNKNOWN"


def print_numeric_buckets(
    trades: List[AnalyzerTrade],
    title: str,
    attribute: str,
    ranges: List[
        Tuple[
            float,
            float,
            str,
        ]
    ],
) -> None:

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    groups: Dict[
        str,
        List[AnalyzerTrade],
    ] = {}

    for trade in trades:

        value = getattr(
            trade,
            attribute,
            None,
        )

        label = bucket_value(
            value,
            ranges,
        )

        groups.setdefault(
            label,
            [],
        ).append(trade)

    labels = [
        item[2]
        for item in ranges
    ]

    labels.append(
        "UNKNOWN"
    )

    for label in labels:

        group = groups.get(
            label,
            [],
        )

        if not group:
            continue

        stats = calculate_statistics(
            group
        )

        print(
            f"{label:<12} | "
            f"Trades: {stats['total']:>3} | "
            f"W: {stats['wins']:>3} | "
            f"L: {stats['losses']:>3} | "
            f"WR: {stats['win_rate']:>6.2f}% | "
            f"R: {stats['total_r']:>7.2f}"
        )


# ============================================================
# LAST TRADES
# ============================================================

def print_last_trades(
    trades: List[AnalyzerTrade],
    count: int = 15,
) -> None:

    print()
    print("=" * 70)
    print("LAST TRADES")
    print("=" * 70)

    for trade in trades[-count:]:

        print(
            f"{str(trade.time):<25} | "
            f"{trade.direction:<4} | "
            f"{trade.result:<6} | "
            f"R={trade.result_r:>5.2f} | "
            f"{trade.sweep_type:<15} | "
            f"V3.1={trade.v31_signal:<4} | "
            f"CONF={trade.confirmations:<2} | "
            f"ALIGN={trade.v31_alignment}"
        )


# ============================================================
# OVERALL REPORT
# ============================================================

def print_overall_report(
    trades: List[AnalyzerTrade],
) -> None:

    stats = calculate_statistics(
        trades
    )

    print()
    print("=" * 70)
    print("XAU_AI V3.1 HISTORICAL STRATEGY ANALYSIS")
    print("=" * 70)

    print(
        f"TOTAL TRADES      : {stats['total']}"
    )

    print(
        f"CLOSED            : {stats['closed']}"
    )

    print(
        f"OPEN              : {stats['open']}"
    )

    print(
        f"WINS              : {stats['wins']}"
    )

    print(
        f"LOSSES            : {stats['losses']}"
    )

    print(
        f"WIN RATE          : {stats['win_rate']:.2f}%"
    )

    print(
        f"TOTAL R           : {stats['total_r']:.2f}"
    )

    print(
        f"AVERAGE R         : {stats['average_r']:.3f}"
    )

    print(
        f"PROFIT FACTOR     : {stats['profit_factor']:.3f}"
    )

    print(
        f"MAX DRAWDOWN      : {stats['max_drawdown']:.2f}R"
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 70)
    print(
        "XAU_AI LIQUIDITY SWEEP STRATEGY ANALYZER V3"
    )
    print("=" * 70)

    print()
    print(
        "Loading historical market data..."
    )

    try:

        df_5m = get_xauusd_candles(
            interval=TIMEFRAME_5M,
            limit=CANDLE_LIMIT_5M,
        )

        df_15m = get_xauusd_candles(
            interval=TIMEFRAME_15M,
            limit=CANDLE_LIMIT_HTF,
        )

        df_1h = get_xauusd_candles(
            interval=TIMEFRAME_1H,
            limit=CANDLE_LIMIT_HTF,
        )

        df_4h = get_xauusd_candles(
            interval=TIMEFRAME_4H,
            limit=CANDLE_LIMIT_HTF,
        )

        df_1d = get_xauusd_candles(
            interval=TIMEFRAME_1D,
            limit=CANDLE_LIMIT_HTF,
        )

    except Exception as exc:

        print()
        print(
            "ERROR LOADING MARKET DATA"
        )

        print(exc)

        return

    # --------------------------------------------------------
    # Prepare
    # --------------------------------------------------------

    df_5m = prepare_dataframe(
        df_5m
    )

    df_15m = prepare_dataframe(
        df_15m
    )

    df_1h = prepare_dataframe(
        df_1h
    )

    df_4h = prepare_dataframe(
        df_4h
    )

    df_1d = prepare_dataframe(
        df_1d
    )

    print(
        f"5M  candles : {len(df_5m)}"
    )

    print(
        f"15M candles : {len(df_15m)}"
    )

    print(
        f"1H  candles : {len(df_1h)}"
    )

    print(
        f"4H  candles : {len(df_4h)}"
    )

    print(
        f"1D  candles : {len(df_1d)}"
    )

    # --------------------------------------------------------
    # Run
    # --------------------------------------------------------

    print()
    print(
        "Running REAL V3.1 "
        "NO-LOOKAHEAD analysis..."
    )

    trades = run_analysis(
        df_5m=df_5m,
        df_15m=df_15m,
        df_1h=df_1h,
        df_4h=df_4h,
        df_1d=df_1d,
    )

    if not trades:

        print()
        print("=" * 70)
        print(
            "NO VALID TRADES FOUND"
        )
        print("=" * 70)

        return

    # --------------------------------------------------------
    # Overall
    # --------------------------------------------------------

    print_overall_report(
        trades
    )

    # --------------------------------------------------------
    # Last trades
    # --------------------------------------------------------

    print_last_trades(
        trades
    )

    # --------------------------------------------------------
    # Main categories
    # --------------------------------------------------------

    print_category_statistics(
        trades,
        "DIRECTION ANALYSIS",
        "direction",
    )

    print_category_statistics(
        trades,
        "LIQUIDITY SWEEP ANALYSIS",
        "sweep_type",
    )

    print_category_statistics(
        trades,
        "5M TREND ANALYSIS",
        "trend_5m",
    )

    print_category_statistics(
        trades,
        "5M STRUCTURE ANALYSIS",
        "structure_5m",
    )

    print_category_statistics(
        trades,
        "1D MAJOR DIRECTION",
        "major_direction",
    )

    print_category_statistics(
        trades,
        "4H STRUCTURE DIRECTION",
        "structure_direction",
    )

    print_category_statistics(
        trades,
        "1H DIRECTION",
        "h1_direction",
    )

    print_category_statistics(
        trades,
        "15M DIRECTION",
        "m15_direction",
    )

    print_category_statistics(
        trades,
        "1D TREND",
        "trend_1d",
    )

    print_category_statistics(
        trades,
        "4H TREND",
        "trend_4h",
    )

    print_category_statistics(
        trades,
        "1H TREND",
        "trend_1h",
    )

    print_category_statistics(
        trades,
        "15M TREND",
        "trend_15m",
    )

    print_category_statistics(
        trades,
        "HTF AGREEMENT",
        "htf_agreement",
    )

    print_category_statistics(
        trades,
        "REAL V3.1 SIGNAL",
        "v31_signal",
    )

    print_category_statistics(
        trades,
        "V3.1 MARKET PHASE",
        "market_phase",
    )

    print_category_statistics(
        trades,
        "V3.1 ENTRY TRIGGER",
        "entry_trigger",
    )

    print_category_statistics(
        trades,
        "5M EMA DIRECTION",
        "ema_direction",
    )

    print_category_statistics(
        trades,
        "5M MACD DIRECTION",
        "macd_direction",
    )

    print_category_statistics(
        trades,
        "5M DMI DIRECTION",
        "dmi_direction",
    )

    print_category_statistics(
        trades,
        "V3.1 CONFIRMATIONS",
        "confirmations",
    )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    print_numeric_buckets(
        trades,
        "RSI ZONE ANALYSIS",
        "rsi",
        [
            (
                0,
                30,
                "<30",
            ),
            (
                30,
                40,
                "30-40",
            ),
            (
                40,
                50,
                "40-50",
            ),
            (
                50,
                60,
                "50-60",
            ),
            (
                60,
                70,
                "60-70",
            ),
            (
                70,
                1000,
                ">70",
            ),
        ],
    )

    # --------------------------------------------------------
    # ADX
    # --------------------------------------------------------

    print_numeric_buckets(
        trades,
        "ADX STRENGTH ANALYSIS",
        "adx",
        [
            (
                0,
                15,
                "<15",
            ),
            (
                15,
                20,
                "15-20",
            ),
            (
                20,
                25,
                "20-25",
            ),
            (
                25,
                30,
                "25-30",
            ),
            (
                30,
                1000,
                ">30",
            ),
        ],
    )

    # --------------------------------------------------------
    # V3.1 Alignment
    # --------------------------------------------------------

    print_numeric_buckets(
        trades,
        "REAL V3.1 ALIGNMENT ANALYSIS",
        "v31_alignment",
        [
            (
                0,
                50,
                "0-49",
            ),
            (
                50,
                70,
                "50-69",
            ),
            (
                70,
                85,
                "70-84",
            ),
            (
                85,
                101,
                "85-100",
            ),
        ],
    )

    # --------------------------------------------------------
    # Finish
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "REAL V3.1 ANALYSIS FINISHED"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()