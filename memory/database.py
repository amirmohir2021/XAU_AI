import sqlite3
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "xau_ai_memory.db"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timeframe TEXT NOT NULL,
            open_time TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL DEFAULT 0,
            tick_volume REAL DEFAULT 0,
            is_open INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(timeframe, open_time)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_candles_tf_time
        ON candles(timeframe, open_time)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_time TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry REAL,
            stop_loss REAL,
            tp1 REAL,
            tp2 REAL,
            confirmations INTEGER,
            alignment REAL,
            market_phase TEXT,
            entry_trigger TEXT,
            result TEXT DEFAULT 'OPEN',
            result_r REAL,
            closed_time TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_time
        ON signals(signal_time)
    """)

    conn.commit()
    conn.close()


def save_candle(
    timeframe: str,
    open_time: str,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float = 0,
    tick_volume: float = 0,
    is_open: bool = False
):
    conn = get_connection()

    conn.execute("""
        INSERT OR REPLACE INTO candles (
            timeframe,
            open_time,
            open,
            high,
            low,
            close,
            volume,
            tick_volume,
            is_open
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timeframe,
        open_time,
        open_price,
        high,
        low,
        close,
        volume,
        tick_volume,
        int(is_open)
    ))

    conn.commit()
    conn.close()


def get_candle_count(timeframe: Optional[str] = None):
    conn = get_connection()

    if timeframe:
        cursor = conn.execute(
            "SELECT COUNT(*) AS count FROM candles WHERE timeframe = ?",
            (timeframe,)
        )
    else:
        cursor = conn.execute(
            "SELECT COUNT(*) AS count FROM candles"
        )

    result = cursor.fetchone()["count"]

    conn.close()

    return result


def get_signal_count():
    conn = get_connection()

    cursor = conn.execute(
        "SELECT COUNT(*) AS count FROM signals"
    )

    result = cursor.fetchone()["count"]

    conn.close()

    return result


def save_signal(
    signal_time: str,
    direction: str,
    entry: Optional[float] = None,
    stop_loss: Optional[float] = None,
    tp1: Optional[float] = None,
    tp2: Optional[float] = None,
    confirmations: Optional[int] = None,
    alignment: Optional[float] = None,
    market_phase: Optional[str] = None,
    entry_trigger: Optional[str] = None,
):
    """
    Save a BUY/SELL signal into the signals table.

    Signals are initially stored as OPEN.
    """

    direction = direction.upper().strip()

    if direction not in {"BUY", "SELL"}:
        raise ValueError(
            f"Invalid signal direction: {direction}. "
            f"Only BUY or SELL can be saved."
        )

    conn = get_connection()

    cursor = conn.execute("""
        INSERT INTO signals (
            signal_time,
            direction,
            entry,
            stop_loss,
            tp1,
            tp2,
            confirmations,
            alignment,
            market_phase,
            entry_trigger,
            result
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
    """, (
        signal_time,
        direction,
        entry,
        stop_loss,
        tp1,
        tp2,
        confirmations,
        alignment,
        market_phase,
        entry_trigger
    ))

    signal_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return signal_id


if __name__ == "__main__":
    initialize_database()

    print("=" * 70)
    print("XAU_AI MEMORY DATABASE")
    print("=" * 70)

    print("Database:", DB_PATH)

    print("15M candles:", get_candle_count("15m"))
    print("5M candles :", get_candle_count("5m"))
    print("1H candles :", get_candle_count("1h"))
    print("4H candles :", get_candle_count("4h"))
    print("1D candles :", get_candle_count("1d"))

    print("Signals:", get_signal_count())

    print("=" * 70)
    print("DATABASE READY")
    print("=" * 70)