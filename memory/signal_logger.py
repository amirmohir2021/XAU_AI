from datetime import datetime, timezone
from typing import Optional

from memory.database import get_connection, save_signal


def log_strategy_signal(result) -> Optional[int]:
    """
    Save a StrategyResult BUY/SELL signal into the database.

    NO_TRADE signals are ignored.

    Duplicate protection:
    The same signal_time + direction + entry is not saved twice.

    Returns:
        signal ID if saved
        existing signal ID if duplicate
        None if NO_TRADE
    """

    signal = getattr(result, "signal", "NO_TRADE")

    if signal not in {"BUY", "SELL"}:
        return None

    analysis_time = getattr(result, "analysis_time", None)

    if analysis_time is None:
        analysis_time = datetime.now(timezone.utc).isoformat()

    signal_time = str(analysis_time)

    entry = getattr(result, "entry", None)

    conn = get_connection()

    existing = conn.execute(
        """
        SELECT id
        FROM signals
        WHERE signal_time = ?
          AND direction = ?
          AND (
              entry = ?
              OR (entry IS NULL AND ? IS NULL)
          )
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            signal_time,
            signal,
            entry,
            entry,
        ),
    ).fetchone()

    conn.close()

    if existing:
        return existing["id"]

    metadata = getattr(result, "metadata", {}) or {}

    signal_id = save_signal(
        signal_time=signal_time,
        direction=signal,
        entry=entry,
        stop_loss=getattr(result, "stop_loss", None),
        tp1=getattr(result, "tp1", None),
        tp2=getattr(result, "tp2", None),
        confirmations=getattr(
            result,
            "confirmation_count",
            None,
        ),
        alignment=metadata.get("v31_confidence"),
        market_phase=metadata.get("v31_market_phase"),
        entry_trigger=metadata.get("v31_entry_trigger"),
    )

    return signal_id