from datetime import datetime, timezone
from pathlib import Path
import sqlite3


# ============================================================
# PROJECT ROOT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "xau_ai_memory.db"


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# RESULT CALCULATION
# ============================================================

def calculate_signal_outcome(
    direction,
    entry,
    stop_loss,
    tp1,
    candles,
):
    """
    Determine signal outcome using future closed 5M candles.

    Rules:

    BUY:
        LOW <= SL  -> LOSS
        HIGH >= TP1 -> WIN

    SELL:
        HIGH >= SL -> LOSS
        LOW <= TP1 -> WIN

    If both SL and TP1 are touched inside
    the same candle, SL is treated as first.

    Returns:
        {
            "result": "WIN" / "LOSS" / "OPEN",
            "result_r": float / None,
            "closed_time": str / None
        }
    """

    if not candles:
        return {
            "result": "OPEN",
            "result_r": None,
            "closed_time": None,
        }

    direction = str(direction).upper().strip()

    try:
        entry = float(entry)
        stop_loss = float(stop_loss)
        tp1 = float(tp1)
    except (TypeError, ValueError):
        return {
            "result": "OPEN",
            "result_r": None,
            "closed_time": None,
        }

    # --------------------------------------------------------
    # RISK
    # --------------------------------------------------------

    risk = abs(entry - stop_loss)

    if risk <= 0:
        return {
            "result": "OPEN",
            "result_r": None,
            "closed_time": None,
        }

    # --------------------------------------------------------
    # CANDLE LOOP
    # --------------------------------------------------------

    for candle in candles:

        candle_time = candle["open_time"]

        try:
            high = float(candle["high"])
            low = float(candle["low"])
        except (TypeError, ValueError):
            continue

        # ====================================================
        # BUY
        # ====================================================

        if direction == "BUY":

            sl_hit = low <= stop_loss
            tp_hit = high >= tp1

            # ------------------------------------------------
            # BOTH HIT
            # ------------------------------------------------

            if sl_hit and tp_hit:

                return {
                    "result": "LOSS",
                    "result_r": -1.0,
                    "closed_time": candle_time,
                }

            # ------------------------------------------------
            # STOP LOSS
            # ------------------------------------------------

            if sl_hit:

                return {
                    "result": "LOSS",
                    "result_r": -1.0,
                    "closed_time": candle_time,
                }

            # ------------------------------------------------
            # TAKE PROFIT
            # ------------------------------------------------

            if tp_hit:

                tp_r = abs(tp1 - entry) / risk

                return {
                    "result": "WIN",
                    "result_r": round(tp_r, 4),
                    "closed_time": candle_time,
                }

        # ====================================================
        # SELL
        # ====================================================

        elif direction == "SELL":

            sl_hit = high >= stop_loss
            tp_hit = low <= tp1

            # ------------------------------------------------
            # BOTH HIT
            # ------------------------------------------------

            if sl_hit and tp_hit:

                return {
                    "result": "LOSS",
                    "result_r": -1.0,
                    "closed_time": candle_time,
                }

            # ------------------------------------------------
            # STOP LOSS
            # ------------------------------------------------

            if sl_hit:

                return {
                    "result": "LOSS",
                    "result_r": -1.0,
                    "closed_time": candle_time,
                }

            # ------------------------------------------------
            # TAKE PROFIT
            # ------------------------------------------------

            if tp_hit:

                tp_r = abs(entry - tp1) / risk

                return {
                    "result": "WIN",
                    "result_r": round(tp_r, 4),
                    "closed_time": candle_time,
                }

    # --------------------------------------------------------
    # STILL OPEN
    # --------------------------------------------------------

    return {
        "result": "OPEN",
        "result_r": None,
        "closed_time": None,
    }


# ============================================================
# LOAD FUTURE CANDLES
# ============================================================

def get_future_candles(
    signal_time,
    timeframe="5m",
):
    """
    Load closed candles after the signal time.

    Only is_open = 0 candles are used.
    """

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            open_time,
            open,
            high,
            low,
            close,
            is_open
        FROM candles
        WHERE timeframe = ?
          AND open_time > ?
          AND is_open = 0
        ORDER BY open_time ASC
        """,
        (
            timeframe,
            signal_time,
        ),
    ).fetchall()

    conn.close()

    return rows


# ============================================================
# UPDATE ONE SIGNAL
# ============================================================

def update_signal_outcome(
    signal_id,
):
    """
    Update one OPEN signal.

    Returns updated result information.
    """

    conn = get_connection()

    signal = conn.execute(
        """
        SELECT *
        FROM signals
        WHERE id = ?
        LIMIT 1
        """,
        (
            signal_id,
        ),
    ).fetchone()

    conn.close()

    if signal is None:

        return {
            "signal_id": signal_id,
            "result": "NOT_FOUND",
            "result_r": None,
            "closed_time": None,
        }

    # --------------------------------------------------------
    # ALREADY CLOSED
    # --------------------------------------------------------

    if signal["result"] in (
        "WIN",
        "LOSS",
    ):

        return {
            "signal_id": signal_id,
            "result": signal["result"],
            "result_r": signal["result_r"],
            "closed_time": signal["closed_time"],
        }

    # --------------------------------------------------------
    # VALIDATE LEVELS
    # --------------------------------------------------------

    required = (
        signal["signal_time"],
        signal["direction"],
        signal["entry"],
        signal["stop_loss"],
        signal["tp1"],
    )

    if any(value is None for value in required):

        return {
            "signal_id": signal_id,
            "result": "OPEN",
            "result_r": None,
            "closed_time": None,
        }

    # --------------------------------------------------------
    # FUTURE CANDLES
    # --------------------------------------------------------

    candles = get_future_candles(
        signal_time=signal["signal_time"],
        timeframe="5m",
    )

    # --------------------------------------------------------
    # CALCULATE
    # --------------------------------------------------------

    outcome = calculate_signal_outcome(
        direction=signal["direction"],
        entry=signal["entry"],
        stop_loss=signal["stop_loss"],
        tp1=signal["tp1"],
        candles=candles,
    )

    # --------------------------------------------------------
    # NO CHANGE
    # --------------------------------------------------------

    if outcome["result"] == "OPEN":

        return {
            "signal_id": signal_id,
            "result": "OPEN",
            "result_r": None,
            "closed_time": None,
        }

    # --------------------------------------------------------
    # UPDATE DATABASE
    # --------------------------------------------------------

    conn = get_connection()

    conn.execute(
        """
        UPDATE signals
        SET
            result = ?,
            result_r = ?,
            closed_time = ?
        WHERE id = ?
        """,
        (
            outcome["result"],
            outcome["result_r"],
            outcome["closed_time"],
            signal_id,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "signal_id": signal_id,
        "result": outcome["result"],
        "result_r": outcome["result_r"],
        "closed_time": outcome["closed_time"],
    }


# ============================================================
# UPDATE ALL OPEN SIGNALS
# ============================================================

def update_all_open_signals():
    """
    Check all OPEN signals against available
    closed 5M candles.
    """

    conn = get_connection()

    signals = conn.execute(
        """
        SELECT id
        FROM signals
        WHERE result = 'OPEN'
        ORDER BY signal_time ASC
        """
    ).fetchall()

    conn.close()

    results = []

    for signal in signals:

        result = update_signal_outcome(
            signal_id=signal["id"]
        )

        results.append(result)

    return results


# ============================================================
# STATISTICS
# ============================================================

def get_outcome_statistics():
    """
    Return current signal outcome statistics.
    """

    conn = get_connection()

    total = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM signals
        """
    ).fetchone()["count"]

    open_count = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM signals
        WHERE result = 'OPEN'
        """
    ).fetchone()["count"]

    win_count = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM signals
        WHERE result = 'WIN'
        """
    ).fetchone()["count"]

    loss_count = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM signals
        WHERE result = 'LOSS'
        """
    ).fetchone()["count"]

    total_r = conn.execute(
        """
        SELECT COALESCE(
            SUM(result_r),
            0
        ) AS total_r
        FROM signals
        WHERE result_r IS NOT NULL
        """
    ).fetchone()["total_r"]

    conn.close()

    closed_count = win_count + loss_count

    if closed_count > 0:

        win_rate = (
            win_count / closed_count
        ) * 100

    else:

        win_rate = 0.0

    return {
        "total": total,
        "open": open_count,
        "wins": win_count,
        "losses": loss_count,
        "closed": closed_count,
        "win_rate": round(
            win_rate,
            2
        ),
        "total_r": round(
            float(total_r or 0),
            4
        ),
    }


# ============================================================
# PRINT SIGNAL HISTORY
# ============================================================

def print_signal_history():
    """
    Print all stored signals.
    """

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            id,
            signal_time,
            direction,
            entry,
            stop_loss,
            tp1,
            tp2,
            confirmations,
            alignment,
            result,
            result_r,
            closed_time
        FROM signals
        ORDER BY id ASC
        """
    ).fetchall()

    conn.close()

    print()
    print("=" * 100)
    print("XAU_AI SIGNAL HISTORY")
    print("=" * 100)

    if not rows:

        print("No BUY/SELL signals recorded.")

        print("=" * 100)

        return

    for row in rows:

        print()
        print(
            f"ID         : {row['id']}"
        )

        print(
            f"TIME       : {row['signal_time']}"
        )

        print(
            f"DIRECTION  : {row['direction']}"
        )

        print(
            f"ENTRY      : {row['entry']}"
        )

        print(
            f"STOP LOSS  : {row['stop_loss']}"
        )

        print(
            f"TP1        : {row['tp1']}"
        )

        print(
            f"TP2        : {row['tp2']}"
        )

        print(
            f"CONFIRM    : {row['confirmations']}"
        )

        print(
            f"ALIGNMENT  : {row['alignment']}"
        )

        print(
            f"RESULT     : {row['result']}"
        )

        print(
            f"RESULT R   : {row['result_r']}"
        )

        print(
            f"CLOSED     : {row['closed_time']}"
        )

        print("-" * 100)

    print("=" * 100)


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 100)
    print("XAU_AI OUTCOME TRACKER")
    print("=" * 100)

    print()
    print(
        f"Database: {DB_PATH}"
    )

    # --------------------------------------------------------
    # UPDATE OPEN SIGNALS
    # --------------------------------------------------------

    results = update_all_open_signals()

    print()
    print(
        f"OPEN SIGNALS CHECKED: {len(results)}"
    )

    if results:

        print()

        for item in results:

            print(
                f"Signal #{item['signal_id']} "
                f"-> {item['result']} "
                f"| R: {item['result_r']} "
                f"| Closed: {item['closed_time']}"
            )

    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    stats = get_outcome_statistics()

    print()
    print("=" * 100)
    print("SIGNAL STATISTICS")
    print("=" * 100)

    print(
        f"TOTAL SIGNALS : {stats['total']}"
    )

    print(
        f"OPEN          : {stats['open']}"
    )

    print(
        f"WINS          : {stats['wins']}"
    )

    print(
        f"LOSSES        : {stats['losses']}"
    )

    print(
        f"CLOSED        : {stats['closed']}"
    )

    print(
        f"WIN RATE      : {stats['win_rate']}%"
    )

    print(
        f"TOTAL R       : {stats['total_r']}"
    )

    print("=" * 100)

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    print_signal_history()

    print()
    print(
        "OUTCOME TRACKER READY"
    )

    print("=" * 100)