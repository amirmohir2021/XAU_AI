from pathlib import Path

import pandas as pd

from analysis.scalping_5m import (
    analyze_5m,
    detect_liquidity_sweep,
)
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
# HELPERS
# ============================================================

def normalize_ohlc(df):
    """
    OHLC dataframe ustunlarini standart holatga keltiradi.
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
            "DataFrame'da datetime yoki openTime yo'q."
        )

    data = data.sort_values(
        "openTime"
    ).reset_index(drop=True)

    return data


def get_latest_closed_before(
    df,
    timestamp,
):
    """
    timestamp'dan OLDIN mavjud bo'lgan oxirgi candle'ni
    qaytaradi.

    Muhim:
    signal timestampidagi hali yopilmagan candle ishlatilmaydi.

    Bu historical analysis uchun lookahead bias'ni
    oldini olishning asosiy qoidalaridan biri.
    """

    data = df[
        df["openTime"] < timestamp
    ]

    if data.empty:
        return None

    return data.iloc[-1]


def get_closed_history(
    df,
    timestamp,
    limit=None,
):
    """
    Faqat signal timestampidan OLDIN yopilgan
    candle'larni qaytaradi.
    """

    data = df[
        df["openTime"] < timestamp
    ]

    if limit is not None:
        data = data.tail(limit)

    return data.reset_index(drop=True)


def direction_from_indicators(
    indicators,
):
    """
    analysis.indicators natijasidan yo'nalish chiqaradi.

    V3.1 bilan bir xil asosiy yo'nalish mantig'idan foydalanadi.
    """

    if not indicators:
        return "NEUTRAL"

    bullish = 0
    bearish = 0

    price = indicators.get("price")
    ema20 = indicators.get("ema20")
    ema50 = indicators.get("ema50")
    ema200 = indicators.get("ema200")
    rsi = indicators.get("rsi14")
    macd = indicators.get("macd")
    macd_signal = indicators.get("macd_signal")
    di_plus = indicators.get("di_plus")
    di_minus = indicators.get("di_minus")

    # --------------------------------------------------------
    # PRICE vs EMA20
    # --------------------------------------------------------

    if (
        price is not None
        and ema20 is not None
    ):

        if price > ema20:
            bullish += 2

        elif price < ema20:
            bearish += 2

    # --------------------------------------------------------
    # EMA20 vs EMA50
    # --------------------------------------------------------

    if (
        ema20 is not None
        and ema50 is not None
    ):

        if ema20 > ema50:
            bullish += 2

        elif ema20 < ema50:
            bearish += 2

    # --------------------------------------------------------
    # PRICE vs EMA200
    # --------------------------------------------------------

    if (
        price is not None
        and ema200 is not None
    ):

        if price > ema200:
            bullish += 1

        elif price < ema200:
            bearish += 1

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if rsi is not None:

        if rsi >= 55:
            bullish += 2

        elif rsi <= 45:
            bearish += 2

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    if (
        macd is not None
        and macd_signal is not None
    ):

        if macd > macd_signal:
            bullish += 1

        elif macd < macd_signal:
            bearish += 1

    # --------------------------------------------------------
    # DI
    # --------------------------------------------------------

    if (
        di_plus is not None
        and di_minus is not None
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
    Historical timestamp uchun HTF analysis.

    Muhim:
    Har bir timeframe'da faqat timestamp'dan OLDIN
    yopilgan candle'lar ishlatiladi.

    Hozircha V3.1 final signalini emas,
    timeframe direction'larini research qilamiz.
    """

    histories = {
        "1d": get_closed_history(
            df_1d,
            timestamp,
            WARMUP_1D,
        ),
        "4h": get_closed_history(
            df_4h,
            timestamp,
            WARMUP_4H,
        ),
        "1h": get_closed_history(
            df_1h,
            timestamp,
            WARMUP_1H,
        ),
        "15m": get_closed_history(
            df_15m,
            timestamp,
            WARMUP_15M,
        ),
    }

    result = {}

    for timeframe, data in histories.items():

        if len(data) < MIN_HTF_CANDLES:
            result[timeframe] = {
                "direction": "NEUTRAL",
                "indicators": {},
                "candles": len(data),
            }
            continue

        try:

            indicators = calculate_indicators(
                data
            )

            direction = direction_from_indicators(
                indicators
            )

            result[timeframe] = {
                "direction": direction,
                "indicators": indicators,
                "candles": len(data),
            }

        except Exception as exc:

            result[timeframe] = {
                "direction": "NEUTRAL",
                "indicators": {},
                "candles": len(data),
                "error": str(exc),
            }

    return result


# ============================================================
# 5M SWEEP ANALYSIS
# ============================================================

def analyze_5m_at_time(
    df_5m,
    timestamp,
):
    """
    Historical 5M analysis.

    Sweep signal timestampidan OLDIN yopilgan candle'lar
    asosida aniqlanadi.

    analyze_5m() oxirgi candle'ni current candle deb qabul
    qilishi sababli timestamp'dan oldingi closed history
    beriladi.
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
# HTF PATTERN
# ============================================================

def get_htf_pattern(
    htf,
):
    return (
        htf["1d"]["direction"],
        htf["4h"]["direction"],
        htf["1h"]["direction"],
        htf["15m"]["direction"],
    )


# ============================================================
# SETUP CLASSIFICATION
# ============================================================

def classify_setup(
    htf,
    direction_5m,
    liquidity_sweep,
):
    """
    Research setup classification.

    Bu hali strategiyaning yakuniy qoidasi EMAS.

    Faqat tarixdagi setup'larni kategoriyalash uchun ishlatiladi.
    """

    d1 = htf["1d"]["direction"]
    h4 = htf["4h"]["direction"]
    h1 = htf["1h"]["direction"]
    m15 = htf["15m"]["direction"]

    # --------------------------------------------------------
    # CURRENT STRICT V3.1 STYLE
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
    # HTF + SWEEP
    # --------------------------------------------------------

    if (
        d1 == "BULLISH"
        and h4 == "BULLISH"
        and liquidity_sweep == "BULLISH_SWEEP"
        and direction_5m == "BULLISH"
    ):

        return "HTF_SWEEP_BULLISH"

    if (
        d1 == "BEARISH"
        and h4 == "BEARISH"
        and liquidity_sweep == "BEARISH_SWEEP"
        and direction_5m == "BEARISH"
    ):

        return "HTF_SWEEP_BEARISH"

    # --------------------------------------------------------
    # RETRACEMENT + SWEEP
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
    # SWEEP ONLY
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

    step:
        Har N-chi 5M candle'da tekshirish.

    Default:
        step=1

    Muhim:
    Bu engine hozircha outcome hisoblamaydi.

    Maqsad:
        tarixdagi setup'larni aniqlash.
    """

    print(
        "=" * 70
    )
    print(
        "XAU_AI HISTORICAL RESEARCH ENGINE V5"
    )
    print(
        "=" * 70
    )

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
    # RESAMPLE
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

    start_index = WARMUP_5M

    print(
        "\nScanning historical 5M candles..."
    )

    for index in range(
        start_index,
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

        # ----------------------------------------------------
        # Faqat sweep mavjud bo'lsa HTF analysis
        # ----------------------------------------------------

        if liquidity_sweep == "NONE":
            continue

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

        result = {
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

        results.append(
            result
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
        "HISTORICAL RESEARCH SUMMARY"
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

    print(
        "\nLIQUIDITY SWEEP:"
    )

    print(
        results[
            "liquidity_sweep"
        ].value_counts().to_string()
    )

    print(
        "\n5M DIRECTION:"
    )

    print(
        results[
            "direction_5m"
        ].value_counts().to_string()
    )

    print(
        "\nSETUP DISTRIBUTION:"
    )

    print(
        results[
            "setup"
        ].value_counts().to_string()
    )

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
            ].value_counts().to_string()
        )

    print(
        "\nHTF PATTERNS:"
    )

    pattern_counts = (
        results[
            [
                "1d",
                "4h",
                "1h",
                "15m",
            ]
        ]
        .value_counts()
        .head(15)
    )

    print(
        pattern_counts.to_string()
    )

    print(
        "\nTOP SETUPS:"
    )

    setup_counts = (
        results[
            "setup"
        ]
        .value_counts()
    )

    for setup, count in setup_counts.items():

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
        f"Results saved:"
    )

    print(
        output
    )

    print(
        "=" * 70
    )