from pathlib import Path

import pandas as pd


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
# TIMEFRAME RESAMPLE
# ============================================================

RESAMPLE_RULES = {
    "5m": "5min",
    "15m": "15min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1D",
}


# ============================================================
# LOAD 5M
# ============================================================

def load_historical_5m(
    path=DEFAULT_5M_PATH
):
    """
    Historical XAUUSD 5M CSV faylini yuklaydi.

    Muhim:
    - UTC timestamp
    - duplicate candle olib tashlanadi
    - vaqt bo'yicha sort qilinadi
    - OHLC numeric qilinadi
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Historical CSV topilmadi: {path}"
        )

    df = pd.read_csv(path)

    required_columns = [
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "CSV'da kerakli ustunlar yo'q: "
            f"{missing}"
        )

    # --------------------------------------------------------
    # DATETIME
    # --------------------------------------------------------

    df["datetime"] = pd.to_datetime(
        df["datetime"],
        utc=True,
        errors="coerce"
    )

    # --------------------------------------------------------
    # NUMERIC
    # --------------------------------------------------------

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # --------------------------------------------------------
    # CLEAN
    # --------------------------------------------------------

    df = df.dropna(
        subset=[
            "datetime",
            "open",
            "high",
            "low",
            "close",
        ]
    )

    df = df.drop_duplicates(
        subset=["datetime"]
    )

    df = df.sort_values(
        "datetime"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # OHLC INTEGRITY
    # --------------------------------------------------------

    invalid_ohlc = (
        (df["high"] < df["open"])
        | (df["high"] < df["close"])
        | (df["low"] > df["open"])
        | (df["low"] > df["close"])
        | (df["high"] < df["low"])
    )

    invalid_count = int(
        invalid_ohlc.sum()
    )

    if invalid_count > 0:

        print(
            f"WARNING: {invalid_count} ta "
            "noto'g'ri OHLC candle olib tashlandi."
        )

        df = df.loc[
            ~invalid_ohlc
        ].reset_index(drop=True)

    return df


# ============================================================
# CLOSED 5M
# ============================================================

def get_closed_5m(
    path=DEFAULT_5M_PATH
):
    """
    Historical CSV'da open/current candle
    mavjud bo'lsa, oxirgi candle'ni tekshiradi.

    CSV tarixiy dataset bo'lgani uchun default holatda
    barcha candle'lar closed hisoblanadi.

    Lekin xavfsizlik uchun oxirgi candle vaqtini
    tekshirish analyzer zimmasida qoladi.
    """

    return load_historical_5m(path)


# ============================================================
# RESAMPLE
# ============================================================

def resample_ohlcv(
    df,
    timeframe
):
    """
    5M OHLCV ma'lumotdan yuqori timeframe yaratadi.

    timeframe:
        5m
        15m
        1h
        4h
        1d
    """

    if timeframe not in RESAMPLE_RULES:
        raise ValueError(
            f"Noto'g'ri timeframe: {timeframe}. "
            f"Mavjud: {list(RESAMPLE_RULES.keys())}"
        )

    if df.empty:
        return pd.DataFrame(
            columns=[
                "openTime",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )

    data = df.copy()

    if "datetime" not in data.columns:

        if "openTime" in data.columns:

            data["datetime"] = pd.to_datetime(
                data["openTime"],
                utc=True
            )

        else:
            raise ValueError(
                "DataFrame'da datetime yoki "
                "openTime mavjud emas."
            )

    data["datetime"] = pd.to_datetime(
        data["datetime"],
        utc=True
    )

    data = data.sort_values(
        "datetime"
    )

    data = data.drop_duplicates(
        subset=["datetime"]
    )

    data = data.set_index(
        "datetime"
    )

    rule = RESAMPLE_RULES[
        timeframe
    ]

    result = data.resample(
        rule,
        label="left",
        closed="left"
    ).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )

    # Bo'sh timeframe'larni olib tashlash
    result = result.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close",
        ]
    )

    result = result.reset_index()

    result = result.rename(
        columns={
            "datetime": "openTime"
        }
    )

    return result[
        [
            "openTime",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    ].reset_index(drop=True)


# ============================================================
# ALL TIMEFRAMES
# ============================================================

def load_all_historical_timeframes(
    path=DEFAULT_5M_PATH
):
    """
    Bitta 5M historical datasetdan:

    5M
    15M
    1H
    4H
    1D

    timeframe'larni yaratadi.
    """

    base_5m = load_historical_5m(
        path
    )

    result = {}

    for timeframe in [
        "5m",
        "15m",
        "1h",
        "4h",
        "1d",
    ]:

        result[timeframe] = resample_ohlcv(
            base_5m,
            timeframe
        )

    return result


# ============================================================
# DATASET VALIDATION
# ============================================================

def validate_historical_dataset(
    df_5m
):
    """
    5M dataset sifatini tekshiradi.
    """

    if df_5m.empty:
        raise ValueError(
            "5M dataset bo'sh."
        )

    times = pd.to_datetime(
        df_5m["datetime"],
        utc=True
    )

    # Duplicate
    duplicate_count = int(
        times.duplicated().sum()
    )

    # Tartib
    sorted_ok = bool(
        times.is_monotonic_increasing
    )

    # Candle gaplari
    deltas = (
        times.diff()
        .dropna()
    )

    expected = pd.Timedelta(
        minutes=5
    )

    normal_count = int(
        (deltas == expected).sum()
    )

    gap_count = int(
        (deltas > expected).sum()
    )

    return {
        "rows": len(df_5m),
        "first": times.iloc[0],
        "last": times.iloc[-1],
        "duplicates": duplicate_count,
        "sorted": sorted_ok,
        "normal_5m_intervals": normal_count,
        "gaps": gap_count,
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print(
        "XAU_AI HISTORICAL DATA ADAPTER TEST"
    )
    print("=" * 70)

    print(
        f"\nCSV: {DEFAULT_5M_PATH}"
    )

    print(
        "\nLoading historical 5M..."
    )

    data = load_all_historical_timeframes()

    print(
        "\n" + "=" * 70
    )
    print(
        "TIMEFRAME SUMMARY"
    )
    print(
        "=" * 70
    )

    for timeframe, df in data.items():

        print(
            f"\n{timeframe.upper()}:"
        )

        print(
            f"  Candles : {len(df)}"
        )

        if not df.empty:

            print(
                f"  First   : {df.iloc[0]['openTime']}"
            )

            print(
                f"  Last    : {df.iloc[-1]['openTime']}"
            )

    print(
        "\n" + "=" * 70
    )
    print(
        "5M DATASET VALIDATION"
    )
    print(
        "=" * 70
    )

    base = load_historical_5m()

    validation = validate_historical_dataset(
        base
    )

    for key, value in validation.items():

        print(
            f"{key}: {value}"
        )

    print(
        "\n" + "=" * 70
    )
    print(
        "TEST YAKUNLANDI"
    )
    print(
        "=" * 70
    )