
import sys
from pathlib import Path

# ============================================================
# XAU_AI loyiha papkasini Python PATH ga qo'shish
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# ============================================================
# XAU_AI modullarini import qilish
# ============================================================

from data.market_data import get_xauusd_candles
from memory.database import (
    initialize_database,
    save_candle,
    get_candle_count
)


# ============================================================
# Yig'iladigan timeframe'lar
# ============================================================

TIMEFRAMES = {
    "5m": 1000,
    "15m": 1000,
    "1h": 1000,
    "4h": 1000,
    "1d": 500,
}


# ============================================================
# Bitta timeframe ma'lumotlarini yig'ish
# ============================================================

def collect_timeframe(timeframe: str, limit: int) -> int:

    print()
    print("-" * 70)
    print(f"[{timeframe.upper()}] Ma'lumot olinmoqda...")
    print("-" * 70)

    try:

        # BiQuote API'dan candlelarni olish
        df = get_xauusd_candles(
            interval=timeframe,
            limit=limit
        )

        # Ma'lumot kelmagan bo'lsa
        if df is None or df.empty:

            print(f"[{timeframe.upper()}] Ma'lumot kelmadi.")

            return 0


        saved = 0


        # ====================================================
        # Candlelarni SQLite bazaga yozish
        # ====================================================

        for _, row in df.iterrows():

            open_time = row["openTime"]


            # pandas Timestamp -> ISO format
            if hasattr(open_time, "isoformat"):
                open_time = open_time.isoformat()


            # Open / High / Low / Close
            open_price = float(row["open"])
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])


            # Volume mavjud bo'lmasa 0
            volume = float(row.get("volume", 0) or 0)

            tick_volume = float(
                row.get("tickVolume", 0) or 0
            )


            # Hozircha API'dan kelgan candlelarni
            # yopilgan candle sifatida saqlaymiz.
            is_open = bool(
                row.get("isOpen", False)
            )


            # Bazaga saqlash
            save_candle(
                timeframe=timeframe,
                open_time=open_time,
                open_price=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                tick_volume=tick_volume,
                is_open=is_open
            )


            saved += 1


        # Bazadagi jami candlelar
        total = get_candle_count(timeframe)


        print()
        print(f"[{timeframe.upper()}] API candles : {len(df)}")
        print(f"[{timeframe.upper()}] Saqlandi     : {saved}")
        print(f"[{timeframe.upper()}] Bazadagi jami: {total}")


        return saved


    except Exception as e:

        print()
        print(f"[{timeframe.upper()}] XATO:")
        print(e)

        return 0


# ============================================================
# Barcha timeframe'larni yig'ish
# ============================================================

def collect_all():

    print()
    print("=" * 70)
    print("XAU_AI MARKET COLLECTOR")
    print("=" * 70)

    print()
    print("Loyiha papkasi:")
    print(BASE_DIR)

    print()
    print("SQLite memory bazasi ishga tushirilmoqda...")


    # Database yaratish / tekshirish
    initialize_database()


    total_saved = 0


    # ========================================================
    # Timeframe'lar bo'yicha yig'ish
    # ========================================================

    for timeframe, limit in TIMEFRAMES.items():

        saved = collect_timeframe(
            timeframe,
            limit
        )

        total_saved += saved


    # ========================================================
    # Yakuniy natija
    # ========================================================

    print()
    print("=" * 70)
    print("COLLECTOR YAKUNLANDI")
    print("=" * 70)

    print()
    print(
        "Jami qayta ishlangan candle:",
        total_saved
    )


    print()
    print("DATABASE:")


    for timeframe in TIMEFRAMES:

        count = get_candle_count(timeframe)

        print(
            f"{timeframe.upper():>4}: "
            f"{count} candle"
        )


    print()
    print("=" * 70)
    print("MARKET MEMORY READY")
    print("=" * 70)


# ============================================================
# PROGRAM START
# ============================================================

if __name__ == "__main__":
    collect_all()

