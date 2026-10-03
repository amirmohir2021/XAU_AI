from __future__ import annotations

from collections import Counter
from typing import Any, Dict

from memory.database import get_connection


SEPARATOR = "=" * 100


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _calculate_stats(rows) -> Dict[str, Any]:
    total = len(rows)

    wins = 0
    losses = 0
    open_signals = 0

    total_r = 0.0

    for row in rows:
        result = (row["result"] or "OPEN").upper()

        if result == "WIN":
            wins += 1

        elif result == "LOSS":
            losses += 1

        else:
            open_signals += 1

        if result in {"WIN", "LOSS"}:
            total_r += _safe_float(row["result_r"])

    closed = wins + losses

    win_rate = (
        (wins / closed) * 100
        if closed > 0
        else 0.0
    )

    average_r = (
        total_r / closed
        if closed > 0
        else 0.0
    )

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "open": open_signals,
        "closed": closed,
        "win_rate": win_rate,
        "total_r": total_r,
        "average_r": average_r,
    }


def get_all_signal_stats() -> Dict[str, Any]:
    """
    Calculate overall BUY/SELL signal statistics.
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
            market_phase,
            entry_trigger,
            result,
            result_r,
            closed_time
        FROM signals
        ORDER BY signal_time ASC
        """
    ).fetchall()

    conn.close()

    overall = _calculate_stats(rows)

    buy_rows = [
        row for row in rows
        if (row["direction"] or "").upper() == "BUY"
    ]

    sell_rows = [
        row for row in rows
        if (row["direction"] or "").upper() == "SELL"
    ]

    buy_stats = _calculate_stats(buy_rows)
    sell_stats = _calculate_stats(sell_rows)

    return {
        "overall": overall,
        "buy": buy_stats,
        "sell": sell_stats,
    }


def get_confirmation_stats() -> Dict[int, Dict[str, Any]]:
    """
    Calculate performance grouped by confirmation count.

    Example:
        3 confirmations -> 10 signals, 60% win rate
        4 confirmations -> 7 signals, 71.4% win rate
    """

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            confirmations,
            result,
            result_r
        FROM signals
        ORDER BY confirmations ASC
        """
    ).fetchall()

    conn.close()

    grouped: Dict[int, list] = {}

    for row in rows:
        confirmations = row["confirmations"]

        if confirmations is None:
            continue

        confirmations = int(confirmations)

        grouped.setdefault(confirmations, []).append(row)

    stats = {}

    for confirmations, group in sorted(grouped.items()):
        total = len(group)

        wins = sum(
            1
            for row in group
            if (row["result"] or "").upper() == "WIN"
        )

        losses = sum(
            1
            for row in group
            if (row["result"] or "").upper() == "LOSS"
        )

        closed = wins + losses

        total_r = sum(
            _safe_float(row["result_r"])
            for row in group
            if (row["result"] or "").upper() in {"WIN", "LOSS"}
        )

        win_rate = (
            wins / closed * 100
            if closed > 0
            else 0.0
        )

        average_r = (
            total_r / closed
            if closed > 0
            else 0.0
        )

        stats[confirmations] = {
            "total": total,
            "wins": wins,
            "losses": losses,
            "closed": closed,
            "win_rate": win_rate,
            "total_r": total_r,
            "average_r": average_r,
        }

    return stats


def get_alignment_stats() -> Dict[str, Dict[str, Any]]:
    """
    Calculate performance grouped by V3.1 technical alignment.

    Alignment values are grouped into:
        0-49
        50-69
        70-84
        85-100
    """

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            alignment,
            result,
            result_r
        FROM signals
        ORDER BY alignment ASC
        """
    ).fetchall()

    conn.close()

    buckets = {
        "0-49": [],
        "50-69": [],
        "70-84": [],
        "85-100": [],
    }

    for row in rows:
        alignment = row["alignment"]

        if alignment is None:
            continue

        alignment = float(alignment)

        if alignment < 50:
            bucket = "0-49"
        elif alignment < 70:
            bucket = "50-69"
        elif alignment < 85:
            bucket = "70-84"
        else:
            bucket = "85-100"

        buckets[bucket].append(row)

    stats = {}

    for bucket, group in buckets.items():
        total = len(group)

        wins = sum(
            1
            for row in group
            if (row["result"] or "").upper() == "WIN"
        )

        losses = sum(
            1
            for row in group
            if (row["result"] or "").upper() == "LOSS"
        )

        closed = wins + losses

        total_r = sum(
            _safe_float(row["result_r"])
            for row in group
            if (row["result"] or "").upper() in {"WIN", "LOSS"}
        )

        win_rate = (
            wins / closed * 100
            if closed > 0
            else 0.0
        )

        average_r = (
            total_r / closed
            if closed > 0
            else 0.0
        )

        stats[bucket] = {
            "total": total,
            "wins": wins,
            "losses": losses,
            "closed": closed,
            "win_rate": win_rate,
            "total_r": total_r,
            "average_r": average_r,
        }

    return stats


def print_stats_block(title: str, stats: Dict[str, Any]) -> None:
    print()
    print(SEPARATOR)
    print(title)
    print(SEPARATOR)

    print(f"TOTAL SIGNALS : {stats['total']}")
    print(f"WINS          : {stats['wins']}")
    print(f"LOSSES        : {stats['losses']}")
    print(f"OPEN          : {stats['open']}")
    print(f"CLOSED        : {stats['closed']}")
    print(f"WIN RATE      : {stats['win_rate']:.2f}%")
    print(f"TOTAL R       : {stats['total_r']:.2f}")
    print(f"AVERAGE R     : {stats['average_r']:.3f}")


def print_confirmation_stats(
    stats: Dict[int, Dict[str, Any]]
) -> None:

    print()
    print(SEPARATOR)
    print("CONFIRMATION ANALYSIS")
    print(SEPARATOR)

    if not stats:
        print("No signal data available.")
        return

    print(
        f"{'CONF':<8}"
        f"{'TOTAL':<10}"
        f"{'WIN':<10}"
        f"{'LOSS':<10}"
        f"{'WIN RATE':<12}"
        f"{'TOTAL R':<12}"
        f"{'AVG R':<10}"
    )

    print("-" * 72)

    for confirmations, data in stats.items():
        print(
            f"{confirmations:<8}"
            f"{data['total']:<10}"
            f"{data['wins']:<10}"
            f"{data['losses']:<10}"
            f"{data['win_rate']:<12.2f}"
            f"{data['total_r']:<12.2f}"
            f"{data['average_r']:<10.3f}"
        )


def print_alignment_stats(
    stats: Dict[str, Dict[str, Any]]
) -> None:

    print()
    print(SEPARATOR)
    print("TECHNICAL ALIGNMENT ANALYSIS")
    print(SEPARATOR)

    print(
        f"{'ALIGNMENT':<12}"
        f"{'TOTAL':<10}"
        f"{'WIN':<10}"
        f"{'LOSS':<10}"
        f"{'WIN RATE':<12}"
        f"{'TOTAL R':<12}"
        f"{'AVG R':<10}"
    )

    print("-" * 76)

    for bucket, data in stats.items():
        print(
            f"{bucket:<12}"
            f"{data['total']:<10}"
            f"{data['wins']:<10}"
            f"{data['losses']:<10}"
            f"{data['win_rate']:<12.2f}"
            f"{data['total_r']:<12.2f}"
            f"{data['average_r']:<10.3f}"
        )


def print_signal_stats() -> None:
    print()
    print(SEPARATOR)
    print("XAU_AI HISTORICAL INTELLIGENCE")
    print(SEPARATOR)

    stats = get_all_signal_stats()

    overall = stats["overall"]
    buy = stats["buy"]
    sell = stats["sell"]

    print_stats_block(
        "OVERALL PERFORMANCE",
        overall,
    )

    print_stats_block(
        "BUY PERFORMANCE",
        buy,
    )

    print_stats_block(
        "SELL PERFORMANCE",
        sell,
    )

    confirmation_stats = get_confirmation_stats()

    print_confirmation_stats(
        confirmation_stats
    )

    alignment_stats = get_alignment_stats()

    print_alignment_stats(
        alignment_stats
    )

    print()
    print(SEPARATOR)
    print("HISTORICAL INTELLIGENCE READY")
    print(SEPARATOR)


if __name__ == "__main__":
    print_signal_stats()