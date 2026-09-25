import sys
import time
from pathlib import Path
from datetime import datetime, timezone

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
# Collector sozlamalari
# ============================================================

TIMEFRAMES = {
    "5m": 1000,
    "15m": 1000,
    "1h": 1000,
    "4h": 1000,
    "1d": 500,
}

# Har bir aylanish orasidagi kutish vaqti
# 60 soniya = 1 daqiqa
COLLECT_INTERVAL = 60


# ============================================================
# Vaqt
# ============================================================

def current_time():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


# ============================================================
# Bitta timeframe'ni yig'ish
# ============================================================

def collect_timeframe(timeframe: str, limit: int) -> int:

    print()
    print("-" * 70)
    print(
        f"[{timeframe.upper()}] "
        f"Ma'lumot olinmoqda..."
    )
    print("-" * 70)

    try:

        df = get_xauusd_candles(
            interval=timeframe,
            limit=limit
        )

        if df is None or df.empty:

            print(
                f"[{timeframe.upper()}] "
                f"Ma'lumot kelmadi."
            )

            return 0


        saved = 0


        for _, row in df.iterrows():

            open_time = row["openTime"]


            # pandas Timestamp -> ISO
            if hasattr(open_time, "isoformat"):
                open_time = open_time.isoformat()


            open_price = float(row["open"])
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])


            # Volume
            volume = float(
                row.get("volume", 0) or 0
            )

            tick_volume = float(
                row.get("tickVolume", 0) or 0
            )


            # Candle ochiq yoki yopiq
            is_open = bool(
                row.get("isOpen", False)
            )


            # SQLite'ga yozish
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


        total = get_candle_count(timeframe)


        print(
            f"[{timeframe.upper()}] "
            f"API: {len(df)} | "
            f"Jami DB: {total}"
        )


        return saved


    except Exception as e:

        print(
            f"[{timeframe.upper()}] "
            f"XATO: {e}"
        )

        return 0


# ============================================================
# Barcha timeframe'larni yig'ish
# ============================================================

def collect_all():

    print()
    print("=" * 70)
    print("XAU_AI MARKET MEMORY COLLECTOR V2")
    print("=" * 70)

    print(
        f"Vaqt: {current_time()}"
    )


    initialize_database()


    total_saved = 0


    for timeframe, limit in TIMEFRAMES.items():

        total_saved += collect_timeframe(
            timeframe,
            limit
        )


    print()
    print("-" * 70)
    print("DATABASE HOLATI")
    print("-" * 70)


    for timeframe in TIMEFRAMES:

        count = get_candle_count(timeframe)

        print(
            f"{timeframe.upper():>4}: "
            f"{count} candle"
        )


    print("-" * 70)

    print(
        f"Qayta ishlangan: {total_saved}"
    )


# ============================================================
# DOIMIY COLLECTOR
# ============================================================

def run_forever():

    print()
    print("=" * 70)
    print("XAU_AI CONTINUOUS MARKET MEMORY")
    print("=" * 70)

    print()
    print(
        "Collector doimiy ishlaydi."
    )

    print(
        f"Tekshirish intervali: "
        f"{COLLECT_INTERVAL} soniya"
    )

    print()
    print(
        "To'xtatish: CTRL + C"
    )

    print("=" * 70)


    while True:

        try:

            collect_all()


            print()
            print(
                f"Keyingi tekshiruv "
                f"{COLLECT_INTERVAL} soniyadan keyin..."
            )


            time.sleep(
                COLLECT_INTERVAL
            )


        except KeyboardInterrupt:

            print()
            print("=" * 70)
            print(
                "COLLECTOR TO'XTATILDI"
            )
            print("=" * 70)

            break


        except Exception as e:

            print()
            print(
                "COLLECTOR XATO:"
            )

            print(e)

            print()
            print(
                f"{COLLECT_INTERVAL} "
                f"soniyadan keyin qayta uriniladi..."
            )

            time.sleep(
                COLLECT_INTERVAL
            )


# ============================================================
# PROGRAM START
# ============================================================

if __name__ == "__main__":

    run_forever()

