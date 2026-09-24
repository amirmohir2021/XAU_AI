import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))



import pandas as pd

from ta.trend import (
    EMAIndicator,
    MACD,
    ADXIndicator
)

from ta.momentum import (
    RSIIndicator,
    StochasticOscillator
)

from ta.volatility import (
    AverageTrueRange,
    BollingerBands
)


def calculate_indicators(df):
    """
    XAU/USD candle ma'lumotlari asosida
    texnik indikatorlarni hisoblaydi.
    """

    df = df.copy()

    # =========================================================
    # EMA
    # =========================================================

    df["EMA20"] = EMAIndicator(
        close=df["close"],
        window=20
    ).ema_indicator()

    df["EMA50"] = EMAIndicator(
        close=df["close"],
        window=50
    ).ema_indicator()

    df["EMA200"] = EMAIndicator(
        close=df["close"],
        window=200
    ).ema_indicator()

    # =========================================================
    # RSI
    # =========================================================

    df["RSI14"] = RSIIndicator(
        close=df["close"],
        window=14
    ).rsi()

    # =========================================================
    # MACD
    # =========================================================

    macd = MACD(
        close=df["close"],
        window_fast=12,
        window_slow=26,
        window_sign=9
    )

    df["MACD"] = macd.macd()

    df["MACD_SIGNAL"] = macd.macd_signal()

    df["MACD_HIST"] = macd.macd_diff()

    # =========================================================
    # ATR
    # =========================================================

    atr = AverageTrueRange(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=14
    )

    df["ATR14"] = atr.average_true_range()

    # =========================================================
    # ADX
    # =========================================================

    adx = ADXIndicator(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=14
    )

    df["ADX14"] = adx.adx()

    df["DI_PLUS"] = adx.adx_pos()

    df["DI_MINUS"] = adx.adx_neg()

    # =========================================================
    # Bollinger Bands
    # =========================================================

    bb = BollingerBands(
        close=df["close"],
        window=20,
        window_dev=2
    )

    df["BB_MIDDLE"] = bb.bollinger_mavg()

    df["BB_HIGH"] = bb.bollinger_hband()

    df["BB_LOW"] = bb.bollinger_lband()

    # =========================================================
    # Stochastic
    # =========================================================

    stochastic = StochasticOscillator(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=14,
        smooth_window=3
    )

    df["STOCH_K"] = stochastic.stoch()

    df["STOCH_D"] = stochastic.stoch_signal()

    return df


def get_latest_indicator_values(df):
    """
    Eng oxirgi candle indikatorlarini qaytaradi.
    """

    last = df.iloc[-1]

    return {
        "price": float(last["close"]),

        "EMA20": float(last["EMA20"]),
        "EMA50": float(last["EMA50"]),
        "EMA200": float(last["EMA200"]),

        "RSI14": float(last["RSI14"]),

        "MACD": float(last["MACD"]),
        "MACD_SIGNAL": float(last["MACD_SIGNAL"]),
        "MACD_HIST": float(last["MACD_HIST"]),

        "ATR14": float(last["ATR14"]),

        "ADX14": float(last["ADX14"]),
        "DI_PLUS": float(last["DI_PLUS"]),
        "DI_MINUS": float(last["DI_MINUS"]),

        "BB_HIGH": float(last["BB_HIGH"]),
        "BB_MIDDLE": float(last["BB_MIDDLE"]),
        "BB_LOW": float(last["BB_LOW"]),

        "STOCH_K": float(last["STOCH_K"]),
        "STOCH_D": float(last["STOCH_D"]),
    }


if __name__ == "__main__":

    # Test uchun data modulidan foydalanamiz

    from data.market_data import get_xauusd_candles

    print("=" * 60)
    print("XAU/USD INDICATOR TEST")
    print("=" * 60)

    # EMA200 uchun kamida 200 candle kerak.
    # Shuning uchun 1D dan 250 ta olamiz.

    df = get_xauusd_candles(
        interval="1d",
        limit=250
    )

    print(
        f"\nCandle soni: {len(df)}"
    )

    # Indikatorlarni hisoblash
    df = calculate_indicators(df)

    print("\nIndikatorlar hisoblandi.")

    # Oxirgi qiymatlar
    latest = get_latest_indicator_values(df)

    print("\n" + "=" * 60)
    print("OXIRGI INDIKATORLAR")
    print("=" * 60)

    for name, value in latest.items():

        print(
            f"{name:15} : {value:.4f}"
        )

    print("\n" + "=" * 60)
    print("OXIRGI 5 TA CANDLE + INDIKATORLAR")
    print("=" * 60)

    columns = [
        "openTime",
        "close",
        "EMA20",
        "EMA50",
        "EMA200",
        "RSI14",
        "MACD",
        "MACD_SIGNAL",
        "ATR14",
        "ADX14"
    ]

    print(
        df[columns].tail(5).to_string(
            index=False
        )
    )

    print("\n" + "=" * 60)
    print("INDICATOR TEST MUVAFFAQIYATLI")
    print("=" * 60)