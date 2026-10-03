from pathlib import Path

import pandas as pd

from analysis.scalping_5m import analyze_5m
from analysis.indicators import calculate_indicators
from strategy_lab.historical_data import (
    load_historical_5m,
    resample_ohlcv,
)


# ============================================================
# PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_5M_PATH = (
    PROJECT_ROOT
    / "data"
    / "historical"
    / "XAUUSD_5m.csv"
)


# ============================================================
# SETTINGS
# ============================================================

WARMUP_5M = 250

WARMUP_15M = 250
WARMUP_1H = 250
WARMUP_4H = 250
WARMUP_1D = 100

MIN_HTF_CANDLES = 50


# ============================================================
# DATAFRAME NORMALIZATION
# ============================================================

def normalize_ohlc(df):
    """
    OHLC dataframe timestampini standart holatga keltiradi.
    """

    data = df.copy()

    if "datetime" in data.columns:

        data["openTime"] = pd.to_datetime(
            data["datetime"],
            utc=True,
        )

    elif "openTime" in data.columns:

        data["openTime"] = pd.to_datetime(
            data["openTime"],
            utc=True,
        )

    else:

        raise ValueError(
            "DataFrame'da datetime yoki openTime mavjud emas."
        )

    data = (
        data
        .sort_values("openTime")
        .drop_duplicates("openTime")
        .reset_index(drop=True)
    )

    return data


# ============================================================
# HISTORICAL CLOSED DATA
# ============================================================

def get_closed_history(
    df,
    timestamp,
    limit=None,
):
    """
    Faqat timestampdan OLDIN mavjud bo'lgan candlelarni qaytaradi.

    Muhim:
    timestamp candle'ining o'zi ishlatilmaydi.

    Shu orqali signal vaqtida hali noma'lum bo'lgan
    candle ma'lumotlaridan foydalanishning oldini olamiz.
    """

    data = df[
        df["openTime"] < timestamp
    ]

    if limit is not None:
        data = data.tail(limit)

    return data.reset_index(drop=True)


# ============================================================
# INDICATOR DIRECTION
# ============================================================

def direction_from_indicator_row(
    row,
):
    """
    analysis.indicators.calculate_indicators()
    qaytargan DataFrame'ning oxirgi qatoridan
    V3.1 yo'nalish mantig'ini chiqaradi.

    Ishlatiladigan ustunlar:
        close
        EMA20
        EMA50
        EMA200
        RSI14
        MACD
        MACD_SIGNAL
        DI_PLUS
        DI_MINUS
    """

    if row is None:
        return "NEUTRAL"

    bullish = 0
    bearish = 0

    # --------------------------------------------------------
    # CLOSE / PRICE
    # --------------------------------------------------------

    price = row.get("close")
    ema20 = row.get("EMA20")
    ema50 = row.get("EMA50")
    ema200 = row.get("EMA200")

    # --------------------------------------------------------
    # PRICE vs EMA20
    # --------------------------------------------------------

    if (
        pd.notna(price)
        and pd.notna(ema20)
    ):

        if price > ema20:
            bullish += 2

        elif price < ema20:
            bearish += 2

    # --------------------------------------------------------
    # EMA20 vs EMA50
    # --------------------------------------------------------

    if (
        pd.notna(ema20)
        and pd.notna(ema50)
    ):

        if ema20 > ema50:
            bullish += 2

        elif ema20 < ema50:
            bearish += 2

    # --------------------------------------------------------
    # PRICE vs EMA200
    # --------------------------------------------------------

    if (
        pd.notna(price)
        and pd.notna(ema200)
    ):

        if price > ema200:
            bullish += 1

        elif price < ema200:
            bearish += 1

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    rsi = row.get("RSI14")

    if pd.notna(rsi):

        if rsi >= 55:
            bullish += 2

        elif rsi <= 45:
            bearish += 2

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    macd = row.get("MACD")
    macd_signal = row.get("MACD_SIGNAL")

    if (
        pd.notna(macd)
        and pd.notna(macd_signal)
    ):

        if macd > macd_signal:
            bullish += 1

        elif macd < macd_signal:
            bearish += 1

    # --------------------------------------------------------
    # DI
    # --------------------------------------------------------

    di_plus = row.get("DI_PLUS")
    di_minus = row.get("DI_MINUS")

    if (
        pd.notna(di_plus)
        and pd.notna(di_minus)
    ):

        if di_plus > di_minus:
            bullish += 1

        elif di_plus < di_minus:
            bearish += 1

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    if bullish > bearish and bullish >= 5:
        return "BULLISH"

    if bearish > bullish and bearish >= 5:
        return "BEARISH"

    return "NEUTRAL"


# ============================================================
# HISTORICAL TIMEFRAME DIRECTION
# ============================================================

def calculate_historical_direction(
    df,
    timestamp,
    warmup,
):
    """
    Berilgan historical timestamp uchun timeframe
    directionini hisoblaydi.

    Faqat timestampdan OLDIN yopilgan candlelar ishlatiladi.
    """

    history = get_closed_history(
        df,
        timestamp,
        warmup,
    )

    if len(history) < MIN_HTF_CANDLES:
        return {
            "direction": "NEUTRAL",
            "candles": len(history),
        }

    try:

        indicators = calculate_indicators(
            history
        )

        if indicators.empty:
            return {
                "direction": "NEUTRAL",
                "candles": len(history),
            }

        latest = indicators.iloc[-1]

        direction = direction_from_indicator_row(
            latest
        )

        return {
            "direction": direction,
            "candles": len(history),
            "indicators": latest,
        }

    except Exception as exc:

        return {
            "direction": "NEUTRAL",
            "candles": len(history),
            "error": str(exc),
        }


# ============================================================
# HISTORICAL HTF ANALYSIS
# ============================================================

def analyze_htf_at_time(
    df_1d,
    df_4h,
    df_1h,
    df_15m,
    timestamp,
):
    """
    Historical 1D / 4H / 1H / 15M analysis.
    """

    return {
        "1d": calculate_historical_direction(
            df_1d,
            timestamp,
            WARMUP_1D,
        ),
        "4h": calculate_historical_direction(
            df_4h,
            timestamp,
            WARMUP_4H,
        ),
        "1h": calculate_historical_direction(
            df_1h,
            timestamp,
            WARMUP_1H,
        ),
        "15m": calculate_historical_direction(
            df_15m,
            timestamp,
            WARMUP_15M,
        ),
    }


# ============================================================
# 5M HISTORICAL ANALYSIS
# ============================================================

def analyze_5m_at_time(
    df_5m,
    timestamp,
):
    """
    Historical 5M analysis.

    Faqat timestampdan OLDIN yopilgan candlelar beriladi.
    """

    history = get_closed_history(
        df_5m,
        timestamp,
        WARMUP_5M,
    )

    if len(history) < WARMUP_5M:

        return {
            "ready": False,
            "direction": "NEUTRAL",
            "liquidity_sweep": "NONE",
            "atr": None,
        }

    try:

        analysis = analyze_5m(
            history
        )

        return {
            "ready": True,
            "direction": analysis.get(
                "direction",
                "NEUTRAL",
            ),
            "liquidity_sweep": analysis.get(
                "liquidity_sweep",
                "NONE",
            ),
            "atr": analysis.get(
                "atr"
            ),
            "analysis": analysis,
        }

    except Exception as exc:

        return {
            "ready": False,
            "direction": "NEUTRAL",
            "liquidity_sweep": "NONE",
            "atr": None,
            "error": str(exc),
        }


# ============================================================
# SETUP CLASSIFICATION
# ============================================================

def classify_setup(
    htf,
    direction_5m,
    liquidity_sweep,
):
    """
    Historical research setup classification.

    Bu hali yakuniy trading qoidasi emas.
    Research uchun kategoriyalar.
    """

    d1 = htf["1d"]["direction"]
    h4 = htf["4h"]["direction"]
    h1 = htf["1h"]["direction"]
    m15 = htf["15m"]["direction"]

    # --------------------------------------------------------
    # STRICT BULLISH
    # --------------------------------------------------------

    if (
        d1 == "BULLISH"
        and h4 == "BULLISH"
        and h1 == "BULLISH"
        and m15 == "BULLISH"
        and direction_5m == "BULLISH"
        and liquidity_sweep == "BULLISH_SWEEP"
    ):

        return "STRICT_BULLISH"

    # --------------------------------------------------------
    # STRICT BEARISH
    # --------------------------------------------------------

    if (
        d1 == "BEARISH"
        and h4 == "BEARISH"
        and h1 == "BEARISH"
        and m15 == "BEARISH"
        and direction_5m == "BEARISH"
        and liquidity_sweep == "BEARISH_SWEEP"
    ):

        return "STRICT_BEARISH"

    # --------------------------------------------------------
    # HTF + SWEEP BULLISH
    # --------------------------------------------------------

    if (
        d1 == "BULLISH"
        and h4 == "BULLISH"
        and liquidity_sweep == "BULLISH_SWEEP"
        and direction_5m == "BULLISH"
    ):

        return "HTF_SWEEP_BULLISH"

    # --------------------------------------------------------
    # HTF + SWEEP BEARISH
    # --------------------------------------------------------

    if (
        d1 == "BEARISH"
        and h4 == "BEARISH"
        and liquidity_sweep == "BEARISH_SWEEP"
        and direction_5m == "BEARISH"
    ):

        return "HTF_SWEEP_BEARISH"

    # --------------------------------------------------------
    # RETRACEMENT BULLISH
    # --------------------------------------------------------

    if (
        d1 == "BULLISH"
        and h4 == "BULLISH"
        and h1 == "BEARISH"
        and m15 == "BEARISH"
        and liquidity_sweep == "BULLISH_SWEEP"
        and direction_5m == "BULLISH"
    ):

        return "RETRACEMENT_BULLISH"

    # --------------------------------------------------------
    # RETRACEMENT BEARISH
    # --------------------------------------------------------

    if (
        d1 == "BEARISH"
        and h4 == "BEARISH"
        and h1 == "BULLISH"
        and m15 == "BULLISH"
        and liquidity_sweep == "BEARISH_SWEEP"
        and direction_5m == "BEARISH"
    ):

        return "RETRACEMENT_BEARISH"

    # --------------------------------------------------------
    # 5M SWEEP ONLY
    # --------------------------------------------------------

    if (
        liquidity_sweep == "BULLISH_SWEEP"
        and direction_5m == "BULLISH"
    ):

        return "SWEEP_5M_BULLISH"

    if (
        liquidity_sweep == "BEARISH_SWEEP"
        and direction_5m == "BEARISH"
    ):

        return "SWEEP_5M_BEARISH"

    return "NO_SETUP"


# ============================================================
# RESEARCH ENGINE
# ============================================================

def run_historical_research(
    path=DEFAULT_5M_PATH,
    step=1,
):
    """
    Historical research engine.

    Lookahead bias qoidasi:
        signal timestampidan keyingi ma'lumot
        signal aniqlashda ishlatilmaydi.
    """

    print(
        "=" * 70
    )
    print(
        "XAU_AI HISTORICAL RESEARCH ENGINE V5.1"
    )
    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    print(
        "\nLoading 5M historical data..."
    )

    base_5m = load_historical_5m(
        path
    )

    print(
        f"Loaded 5M candles: {len(base_5m)}"
    )

    # --------------------------------------------------------
    # TIMEFRAMES
    # --------------------------------------------------------

    print(
        "\nBuilding historical timeframes..."
    )

    df_5m = normalize_ohlc(
        base_5m
    )

    df_15m = normalize_ohlc(
        resample_ohlcv(
            base_5m,
            "15m",
        )
    )

    df_1h = normalize_ohlc(
        resample_ohlcv(
            base_5m,
            "1h",
        )
    )

    df_4h = normalize_ohlc(
        resample_ohlcv(
            base_5m,
            "4h",
        )
    )

    df_1d = normalize_ohlc(
        resample_ohlcv(
            base_5m,
            "1d",
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

    # --------------------------------------------------------
    # SCAN
    # --------------------------------------------------------

    results = []

    total = len(df_5m)

    print(
        "\nScanning historical 5M candles..."
    )

    for index in range(
        WARMUP_5M,
        total,
        step,
    ):

        row = df_5m.iloc[index]

        timestamp = row["openTime"]

        # ----------------------------------------------------
        # 5M
        # ----------------------------------------------------

        analysis_5m = analyze_5m_at_time(
            df_5m,
            timestamp,
        )

        if not analysis_5m["ready"]:
            continue

        liquidity_sweep = analysis_5m[
            "liquidity_sweep"
        ]

        if liquidity_sweep == "NONE":
            continue

        # ----------------------------------------------------
        # HTF
        # ----------------------------------------------------

        htf = analyze_htf_at_time(
            df_1d,
            df_4h,
            df_1h,
            df_15m,
            timestamp,
        )

        direction_5m = analysis_5m[
            "direction"
        ]

        setup = classify_setup(
            htf,
            direction_5m,
            liquidity_sweep,
        )

        results.append(
            {
                "timestamp": timestamp,
                "price": float(
                    row["close"]
                ),
                "liquidity_sweep": liquidity_sweep,
                "direction_5m": direction_5m,
                "setup": setup,
                "1d": htf["1d"]["direction"],
                "4h": htf["4h"]["direction"],
                "1h": htf["1h"]["direction"],
                "15m": htf["15m"]["direction"],
                "atr_5m": analysis_5m["atr"],
            }
        )

    return pd.DataFrame(
        results
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    results,
):
    print(
        "\n" + "=" * 70
    )
    print(
        "HISTORICAL RESEARCH SUMMARY V5.1"
    )
    print(
        "=" * 70
    )

    if results.empty:

        print(
            "\nNo sweep setups found."
        )

        return

    print(
        f"\nTotal sweep points: {len(results)}"
    )

    # --------------------------------------------------------
    # SWEEP
    # --------------------------------------------------------

    print(
        "\nLIQUIDITY SWEEP:"
    )

    print(
        results[
            "liquidity_sweep"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # 5M
    # --------------------------------------------------------

    print(
        "\n5M DIRECTION:"
    )

    print(
        results[
            "direction_5m"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # SETUPS
    # --------------------------------------------------------

    print(
        "\nSETUP DISTRIBUTION:"
    )

    print(
        results[
            "setup"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # HTF
    # --------------------------------------------------------

    print(
        "\nHTF DIRECTION:"
    )

    for timeframe in [
        "1d",
        "4h",
        "1h",
        "15m",
    ]:

        print(
            f"\n{timeframe.upper()}:"
        )

        print(
            results[
                timeframe
            ]
            .value_counts()
            .to_string()
        )

    # --------------------------------------------------------
    # HTF PATTERNS
    # --------------------------------------------------------

    print(
        "\nHTF PATTERNS:"
    )

    patterns = (
        results[
            [
                "1d",
                "4h",
                "1h",
                "15m",
            ]
        ]
        .value_counts()
        .head(20)
    )

    print(
        patterns.to_string()
    )

    # --------------------------------------------------------
    # KEY RESEARCH SETUPS
    # --------------------------------------------------------

    print(
        "\nKEY RESEARCH SETUPS:"
    )

    for setup in [
        "STRICT_BULLISH",
        "STRICT_BEARISH",
        "HTF_SWEEP_BULLISH",
        "HTF_SWEEP_BEARISH",
        "RETRACEMENT_BULLISH",
        "RETRACEMENT_BEARISH",
        "SWEEP_5M_BULLISH",
        "SWEEP_5M_BEARISH",
    ]:

        count = int(
            (
                results["setup"]
                == setup
            ).sum()
        )

        print(
            f"  {setup:<25} {count}"
        )


# ============================================================
# SAVE
# ============================================================

def save_results(
    results,
):
    output_dir = (
        PROJECT_ROOT
        / "data"
        / "historical"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / "historical_research_v5.csv"
    )

    results.to_csv(
        output_path,
        index=False,
    )

    return output_path


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    results = run_historical_research()

    print_summary(
        results
    )

    output = save_results(
        results
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "Results saved:"
    )

    print(
        output
    )

    print(
        "=" * 70
    )