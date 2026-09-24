import requests
import pandas as pd

from datetime import datetime, timedelta, timezone


API_URL = "https://biquote.io/api/XAUUSD/ohlc"


# ============================================================
# TIMEFRAME SOZLAMALARI
# ============================================================

TIMEFRAME_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}


# ============================================================
# API'DAN BIR MARTALIK OLISH
# ============================================================

def _fetch_ohlc_chunk(
    interval="1h",
    limit=1000,
    from_time=None,
    to_time=None
):
    """
    BiQuote API'dan OHLC ma'lumotlarini bir marta oladi.

    API maksimal 1000 barni qo'llab-quvvatlaydi.
    """

    params = {
        "interval": interval,
        "limit": min(int(limit), 1000),
    }

    if from_time is not None:
        params["from"] = from_time

    if to_time is not None:
        params["to"] = to_time

    response = requests.get(
        API_URL,
        params=params,
        timeout=20
    )

    if response.status_code != 200:
        raise Exception(
            f"API xatosi: {response.status_code}\n"
            f"{response.text}"
        )

    data = response.json()

    if "bars" not in data:
        raise Exception(
            "API javobida 'bars' topilmadi:\n"
            f"{data}"
        )

    bars = data["bars"]

    if not bars:
        return []

    return bars


# ============================================================
# DATAFRAMEGA AYLANTIRISH
# ============================================================

def _bars_to_dataframe(bars):
    """
    API'dan kelgan bars ro'yxatini DataFrame qiladi.
    """

    if not bars:
        return pd.DataFrame(
            columns=[
                "openTime",
                "open",
                "high",
                "low",
                "close",
            ]
        )

    df = pd.DataFrame(bars)

    if "openTime" not in df.columns:
        raise Exception(
            "API ma'lumotida openTime topilmadi."
        )

    df["openTime"] = pd.to_datetime(
        df["openTime"],
        utc=True
    )

    for column in [
        "open",
        "high",
        "low",
        "close"
    ]:

        if column not in df.columns:
            raise Exception(
                f"API ma'lumotida '{column}' topilmadi."
            )

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Keraksiz yoki noto'g'ri candle'larni olib tashlash
    df = df.dropna(
        subset=[
            "openTime",
            "open",
            "high",
            "low",
            "close",
        ]
    )

    # Bir xil candle takrorlangan bo'lsa olib tashlash
    df = df.drop_duplicates(
        subset=["openTime"]
    )

    # Eski -> yangi
    df = df.sort_values(
        "openTime"
    ).reset_index(drop=True)

    return df


# ============================================================
# ODDIY SO'ROV
# ============================================================

def get_xauusd_candles(
    interval="1h",
    limit=200
):
    """
    XAU/USD OHLC ma'lumotlarini olish.

    interval:
        1m
        5m
        15m
        30m
        1h
        4h
        1d

    limit:
        kerakli candle soni
    """

    if interval not in TIMEFRAME_MINUTES:
        raise ValueError(
            f"Noto'g'ri interval: {interval}\n"
            f"Mavjud interval'lar: "
            f"{list(TIMEFRAME_MINUTES.keys())}"
        )

    limit = int(limit)

    if limit < 1:
        raise ValueError(
            "limit 1 dan katta bo'lishi kerak."
        )

    if limit > 1000:
        limit = 1000

    bars = _fetch_ohlc_chunk(
        interval=interval,
        limit=limit
    )

    df = _bars_to_dataframe(bars)

    if df.empty:
        raise Exception(
            f"{interval} uchun candle ma'lumotlari bo'sh!"
        )

    return df


# ============================================================
# TARIXNI SANA BO'YICHA OLISH
# ============================================================

def get_xauusd_historical_candles(
    interval="1h",
    required_bars=300
):
    """
    Ko'proq tarix olishga harakat qiladi.

    Avval oddiy limit orqali so'raydi.
    Agar kerakli candle soni kelmasa,
    sana oralig'i bilan qo'shimcha so'rovlar qiladi.

    Bu EMA200 kabi indikatorlar uchun ishlatiladi.
    """

    if interval not in TIMEFRAME_MINUTES:
        raise ValueError(
            f"Noto'g'ri interval: {interval}"
        )

    required_bars = int(required_bars)

    if required_bars < 1:
        raise ValueError(
            "required_bars 1 dan katta bo'lishi kerak."
        )

    # --------------------------------------------------------
    # 1. Avval maksimal bitta so'rov
    # --------------------------------------------------------

    first_bars = _fetch_ohlc_chunk(
        interval=interval,
        limit=min(required_bars, 1000)
    )

    first_df = _bars_to_dataframe(
        first_bars
    )

    if first_df.empty:
        raise Exception(
            f"{interval} uchun tarixiy ma'lumot olinmadi."
        )

    # Yetarli bo'lsa shu yetadi
    if len(first_df) >= required_bars:

        return first_df.tail(
            required_bars
        ).reset_index(drop=True)

    # --------------------------------------------------------
    # 2. Qo'shimcha tarix olish
    # --------------------------------------------------------

    all_parts = [
        first_df
    ]

    current_oldest = first_df[
        "openTime"
    ].min()

    minutes = TIMEFRAME_MINUTES[
        interval
    ]

    # Har bir qo'shimcha request taxminan 900 candle
    # qamrab oladi.
    chunk_bars = 900

    # 900 candle uchun vaqt oralig'i
    chunk_delta = timedelta(
        minutes=minutes * chunk_bars
    )

    # Maksimal 10 ta qo'shimcha request.
    # Keraksiz cheksiz loop bo'lmasligi uchun.
    for _ in range(10):

        if sum(
            len(part)
            for part in all_parts
        ) >= required_bars:
            break

        to_time = current_oldest

        from_time = (
            current_oldest
            - chunk_delta
        )

        from_iso = (
            from_time
            .to_pydatetime()
            .astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

        to_iso = (
            to_time
            .to_pydatetime()
            .astimezone(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

        try:

            bars = _fetch_ohlc_chunk(
                interval=interval,
                limit=1000,
                from_time=from_iso,
                to_time=to_iso
            )

        except Exception:
            # Qo'shimcha tarix mavjud bo'lmasa,
            # mavjud ma'lumot bilan ishlaymiz.
            break

        if not bars:
            break

        chunk_df = _bars_to_dataframe(
            bars
        )

        if chunk_df.empty:
            break

        all_parts.append(
            chunk_df
        )

        new_oldest = chunk_df[
            "openTime"
        ].min()

        # Agar vaqt bo'yicha oldinga siljish bo'lmasa,
        # loopni to'xtatamiz.
        if new_oldest >= current_oldest:
            break

        current_oldest = new_oldest

    # --------------------------------------------------------
    # 3. Barcha qismlarni birlashtirish
    # --------------------------------------------------------

    df = pd.concat(
        all_parts,
        ignore_index=True
    )

    df = df.drop_duplicates(
        subset=["openTime"]
    )

    df = df.sort_values(
        "openTime"
    ).reset_index(drop=True)

    # Kerakli oxirgi candle'lar
    if len(df) > required_bars:

        df = df.tail(
            required_bars
        ).reset_index(drop=True)

    return df


# ============================================================
# BARCHA TIMEFRAME
# ============================================================

def get_all_timeframes(
    limit=200
):
    """
    15M, 1H, 4H, 1D ma'lumotlarini oladi.
    """

    timeframes = {
        "15M": "15m",
        "1H": "1h",
        "4H": "4h",
        "1D": "1d",
    }

    result = {}

    for name, interval in timeframes.items():

        print(
            f"{name} ma'lumotlari olinmoqda..."
        )

        df = get_xauusd_candles(
            interval=interval,
            limit=limit
        )

        result[name] = df

        print(
            f"{name}: "
            f"{len(df)} ta candle olindi"
        )

    return result


# ============================================================
# EMA200 UCHUN YETARLI TARIX
# ============================================================

def get_all_timeframes_for_analysis(
    required_bars=300
):
    """
    Analyzer uchun barcha timeframe'larni
    yetarli tarix bilan olishga harakat qiladi.

    EMA200 uchun kamida 200 candle kerak.
    300 candle olishga harakat qilamiz.
    """

    timeframes = {
        "1D": "1d",
        "4H": "4h",
        "1H": "1h",
        "15M": "15m",
    }

    result = {}

    for name, interval in timeframes.items():

        print(
            f"{name} tarixiy ma'lumotlari olinmoqda..."
        )

        df = get_xauusd_historical_candles(
            interval=interval,
            required_bars=required_bars
        )

        result[name] = df

        print(
            f"{name}: "
            f"{len(df)} ta candle olindi"
        )

        if len(df) < required_bars:

            print(
                f"OGOHLANTIRISH: {name} uchun "
                f"{required_bars} o'rniga "
                f"{len(df)} ta candle mavjud."
            )

    return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("XAU/USD HISTORICAL DATA TEST")
    print("=" * 70)

    try:

        data = get_all_timeframes_for_analysis(
            required_bars=300
        )

        print("\n" + "=" * 70)
        print("NATIJALAR")
        print("=" * 70)

        for timeframe, df in data.items():

            print(
                f"\n--- {timeframe} ---"
            )

            print(
                f"Candle soni: "
                f"{len(df)}"
            )

            print(
                f"Birinchi candle: "
                f"{df.iloc[0]['openTime']}"
            )

            print(
                f"Oxirgi candle: "
                f"{df.iloc[-1]['openTime']}"
            )

            print(
                "\nOxirgi 3 candle:"
            )

            print(
                df[
                    [
                        "openTime",
                        "open",
                        "high",
                        "low",
                        "close"
                    ]
                ].tail(3).to_string(
                    index=False
                )
            )

        print("\n" + "=" * 70)
        print(
            "HISTORICAL DATA TEST YAKUNLANDI"
        )
        print("=" * 70)

    except Exception as e:

        print("\n" + "=" * 70)
        print("XATOLIK")
        print("=" * 70)

        print(
            f"{type(e).__name__}: {e}"
        )