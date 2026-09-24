import requests
import pandas as pd


API_URL = "https://biquote.io/api/XAUUSD/ohlc"


def get_xauusd_candles(interval="1h", limit=200):
    """
    XAU/USD OHLC ma'lumotlarini olish.

    interval:
        15m
        1h
        4h
        1d
    """

    params = {
        "interval": interval,
        "limit": limit
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=15
    )

    if response.status_code != 200:
        raise Exception(
            f"API xatosi: {response.status_code}\n"
            f"{response.text}"
        )

    data = response.json()

    if "bars" not in data:
        raise Exception(
            f"API javobida 'bars' topilmadi:\n{data}"
        )

    bars = data["bars"]

    if not bars:
        raise Exception(
            f"{interval} uchun candle ma'lumotlari bo'sh!"
        )

    df = pd.DataFrame(bars)

    # Vaqtni datetime formatga o'tkazamiz
    df["openTime"] = pd.to_datetime(
        df["openTime"],
        utc=True
    )

    # Narx ustunlarini raqamga o'tkazamiz
    price_columns = [
        "open",
        "high",
        "low",
        "close"
    ]

    for column in price_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Vaqt bo'yicha eski -> yangi
    df = df.sort_values(
        "openTime"
    ).reset_index(drop=True)

    return df


def get_all_timeframes():
    """
    15M, 1H, 4H va 1D ma'lumotlarini oladi.
    """

    timeframes = {
        "15M": "15m",
        "1H": "1h",
        "4H": "4h",
        "1D": "1d"
    }

    result = {}

    for name, interval in timeframes.items():

        print(f"{name} ma'lumotlari olinmoqda...")

        df = get_xauusd_candles(
            interval=interval,
            limit=200
        )

        result[name] = df

        print(
            f"{name}: {len(df)} ta candle olindi"
        )

    return result


if __name__ == "__main__":

    try:

        print("=" * 60)
        print("XAU/USD MULTI-TIMEFRAME DATA TEST")
        print("=" * 60)

        all_data = get_all_timeframes()

        print("\n" + "=" * 60)
        print("NATIJALAR")
        print("=" * 60)

        for timeframe, df in all_data.items():

            print(f"\n--- {timeframe} ---")

            print(
                "Candle soni:",
                len(df)
            )

            print(
                "Birinchi candle:",
                df.iloc[0]["openTime"]
            )

            print(
                "Oxirgi candle:",
                df.iloc[-1]["openTime"]
            )

            print("\nOxirgi 3 candle:")

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

        print("\n" + "=" * 60)
        print("TEST MUVAFFAQIYATLI YAKUNLANDI")
        print("=" * 60)

    except Exception as e:

        print("\n" + "=" * 60)
        print("XATOLIK")
        print("=" * 60)

        print(e)