from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

import pandas as pd

from analysis.scalping_5m import analyze_5m
from analysis.scalping_levels import generate_scalping_levels


MIN_CANDLES = 220


@dataclass
class BacktestTrade:
    signal_time: str
    direction: str

    entry: float
    stop_loss: float
    tp1: float
    tp2: float

    risk: float

    result: str
    result_r: float

    exit_time: Optional[str]

    setup: str
    liquidity_sweep: str

    rsi: Optional[float]
    adx: Optional[float]

    structure: str
    bos: Optional[str]


def _safe_float(value):
    try:
        if value is None:
            return None

        return float(value)

    except (TypeError, ValueError):
        return None


def _get_structure_values(analysis):
    """
    analyze_5m() dagi structure qiymatini xavfsiz o'qiydi.

    Ba'zi versiyalarda structure:
        dict

    ba'zilarida:
        string

    bo'lishi mumkin.
    """

    structure_data = analysis.get(
        "structure",
        "UNKNOWN",
    )

    if isinstance(structure_data, dict):

        structure_value = structure_data.get(
            "direction",
            structure_data.get(
                "structure",
                "UNKNOWN",
            ),
        )

        bos_value = structure_data.get(
            "bos"
        )

    else:

        structure_value = str(
            structure_data
        )

        bos_value = analysis.get(
            "bos"
        )

    return (
        str(structure_value),
        bos_value,
    )


def _check_trade_outcome(
    df: pd.DataFrame,
    start_index: int,
    direction: str,
    entry: float,
    stop_loss: float,
    tp1: float,
):
    """
    Signal chiqqandan keyingi candle'larda
    SL yoki TP1 qaysi biri birinchi tegilganini aniqlaydi.

    Agar bitta candle ichida SL va TP1 ikkalasi ham
    tegsa, konservativ tarzda SL birinchi deb olinadi.
    """

    for i in range(
        start_index,
        len(df),
    ):

        candle = df.iloc[i]

        high = _safe_float(
            candle.get("high")
        )

        low = _safe_float(
            candle.get("low")
        )

        if high is None or low is None:
            continue

        candle_time = candle.get(
            "openTime"
        )

        # --------------------------------------------------
        # BUY
        # --------------------------------------------------

        if direction == "BUY":

            hit_sl = low <= stop_loss
            hit_tp = high >= tp1

            # Bir candle ichida ikkalasi ham
            if hit_sl and hit_tp:

                return (
                    "LOSS",
                    -1.0,
                    candle_time,
                )

            if hit_sl:

                return (
                    "LOSS",
                    -1.0,
                    candle_time,
                )

            if hit_tp:

                risk = entry - stop_loss

                if risk <= 0:

                    return (
                        "INVALID",
                        0.0,
                        candle_time,
                    )

                reward = tp1 - entry

                r_value = reward / risk

                return (
                    "WIN",
                    r_value,
                    candle_time,
                )

        # --------------------------------------------------
        # SELL
        # --------------------------------------------------

        elif direction == "SELL":

            hit_sl = high >= stop_loss
            hit_tp = low <= tp1

            # Bir candle ichida ikkalasi ham
            if hit_sl and hit_tp:

                return (
                    "LOSS",
                    -1.0,
                    candle_time,
                )

            if hit_sl:

                return (
                    "LOSS",
                    -1.0,
                    candle_time,
                )

            if hit_tp:

                risk = stop_loss - entry

                if risk <= 0:

                    return (
                        "INVALID",
                        0.0,
                        candle_time,
                    )

                reward = entry - tp1

                r_value = reward / risk

                return (
                    "WIN",
                    r_value,
                    candle_time,
                )

    return (
        "OPEN",
        0.0,
        None,
    )


def _extract_levels(levels):
    """
    generate_scalping_levels() natijasidan
    kerakli trade qiymatlarini oladi.
    """

    if not isinstance(
        levels,
        dict,
    ):
        return None

    status = levels.get(
        "status"
    )

    if status != "READY":
        return None

    direction = levels.get(
        "direction"
    )

    if direction not in (
        "BUY",
        "SELL",
    ):
        return None

    entry = _safe_float(
        levels.get("entry")
    )

    stop_loss = _safe_float(
        levels.get("stop_loss")
    )

    tp1 = _safe_float(
        levels.get("tp1")
    )

    tp2 = _safe_float(
        levels.get("tp2")
    )

    risk = _safe_float(
        levels.get("risk")
    )

    if None in (
        entry,
        stop_loss,
        tp1,
        tp2,
        risk,
    ):
        return None

    return {
        "direction": direction,
        "entry": entry,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "risk": risk,
    }


def run_liquidity_sweep_backtest(
    df: pd.DataFrame,
    max_trades: Optional[int] = None,
):
    """
    Tarixiy 5M dataframe ustida
    Liquidity Sweep strategiyasini backtest qiladi.

    Muhim:
    - Signal yaratishda faqat o'sha vaqtgacha mavjud candle ishlatiladi.
    - Kelajak candle signal yaratishga aralashmaydi.
    - Outcome esa keyingi candle'larda tekshiriladi.
    """

    if df is None or df.empty:

        raise ValueError(
            "DataFrame bo'sh."
        )

    df = df.copy()

    # ------------------------------------------------------
    # TIME
    # ------------------------------------------------------

    if "openTime" in df.columns:

        df["openTime"] = pd.to_datetime(
            df["openTime"],
            utc=True,
            errors="coerce",
        )

    # ------------------------------------------------------
    # CLOSED CANDLES ONLY
    # ------------------------------------------------------

    if "isOpen" in df.columns:

        df = df[
            df["isOpen"] == False
        ].copy()

    # ------------------------------------------------------
    # SORT
    # ------------------------------------------------------

    if "openTime" in df.columns:

        df = df.sort_values(
            "openTime"
        ).reset_index(
            drop=True
        )

    else:

        df = df.reset_index(
            drop=True
        )

    # ------------------------------------------------------
    # MINIMUM DATA
    # ------------------------------------------------------

    if len(df) < MIN_CANDLES:

        raise ValueError(
            f"Kamida {MIN_CANDLES} ta yopilgan "
            f"5M candle kerak. Hozir: {len(df)}"
        )

    trades = []

    start_index = MIN_CANDLES

    # ======================================================
    # MAIN BACKTEST LOOP
    # ======================================================

    for i in range(
        start_index,
        len(df),
    ):

        if max_trades is not None:

            if len(trades) >= max_trades:
                break

        # --------------------------------------------------
        # ONLY HISTORY AVAILABLE AT SIGNAL TIME
        # --------------------------------------------------

        history_df = df.iloc[
            : i + 1
        ].copy()

        try:

            analysis = analyze_5m(
                history_df
            )

        except Exception as exc:

            print(
                f"Analysis error at index {i}: "
                f"{exc}"
            )

            continue

        if not isinstance(
            analysis,
            dict,
        ):
            continue

        # --------------------------------------------------
        # LIQUIDITY SWEEP
        # --------------------------------------------------

        liquidity_sweep = analysis.get(
            "liquidity_sweep"
        )

        if liquidity_sweep not in (
            "BULLISH_SWEEP",
            "BEARISH_SWEEP",
        ):
            continue

        # --------------------------------------------------
        # SCALPING LEVELS
        # --------------------------------------------------

        try:

            levels = generate_scalping_levels(
                history_df,
                analysis,
            )

        except Exception as exc:

            print(
                f"Level generation error at "
                f"index {i}: {exc}"
            )

            continue

        levels = _extract_levels(
            levels
        )

        if levels is None:
            continue

        # --------------------------------------------------
        # DIRECTION
        # --------------------------------------------------

        direction = levels[
            "direction"
        ]

        # --------------------------------------------------
        # SIGNAL TIME
        # --------------------------------------------------

        signal_time = df.iloc[i][
            "openTime"
        ]

        # --------------------------------------------------
        # STRUCTURE
        # --------------------------------------------------

        structure_value, bos_value = (
            _get_structure_values(
                analysis
            )
        )

        # --------------------------------------------------
        # OUTCOME
        # --------------------------------------------------

        result, result_r, exit_time = (
            _check_trade_outcome(
                df=df,
                start_index=i + 1,
                direction=direction,
                entry=levels["entry"],
                stop_loss=levels["stop_loss"],
                tp1=levels["tp1"],
            )
        )

        # --------------------------------------------------
        # INDICATORS
        # --------------------------------------------------

        indicators = analysis.get(
            "indicators",
            {},
        )

        if not isinstance(
            indicators,
            dict,
        ):
            indicators = {}

        rsi = _safe_float(
            indicators.get("rsi")
        )

        adx = _safe_float(
            indicators.get("adx")
        )

        # --------------------------------------------------
        # TRADE
        # --------------------------------------------------

        trade = BacktestTrade(

            signal_time=str(
                signal_time
            ),

            direction=direction,

            entry=levels[
                "entry"
            ],

            stop_loss=levels[
                "stop_loss"
            ],

            tp1=levels[
                "tp1"
            ],

            tp2=levels[
                "tp2"
            ],

            risk=levels[
                "risk"
            ],

            result=result,

            result_r=result_r,

            exit_time=(
                str(exit_time)
                if exit_time is not None
                else None
            ),

            setup=analysis.get(
                "setup",
                "UNKNOWN",
            ),

            liquidity_sweep=(
                liquidity_sweep
            ),

            rsi=rsi,

            adx=adx,

            structure=structure_value,

            bos=bos_value,
        )

        trades.append(
            asdict(trade)
        )

    return trades


def calculate_backtest_statistics(
    trades,
):
    """
    Backtest umumiy statistikasini hisoblaydi.
    """

    total = len(
        trades
    )

    if total == 0:

        return {
            "total": 0,
            "closed": 0,
            "open": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_r": 0.0,
            "average_r": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_r": 0.0,
        }

    # ------------------------------------------------------
    # RESULTS
    # ------------------------------------------------------

    wins = sum(
        1
        for trade in trades
        if trade["result"] == "WIN"
    )

    losses = sum(
        1
        for trade in trades
        if trade["result"] == "LOSS"
    )

    open_trades = sum(
        1
        for trade in trades
        if trade["result"] == "OPEN"
    )

    closed = (
        wins + losses
    )

    # ------------------------------------------------------
    # TOTAL R
    # ------------------------------------------------------

    total_r = sum(
        float(
            trade.get(
                "result_r",
                0.0,
            )
        )
        for trade in trades
    )

    average_r = (
        total_r / total
        if total
        else 0.0
    )

    # ------------------------------------------------------
    # PROFIT FACTOR
    # ------------------------------------------------------

    win_r = sum(
        float(
            trade.get(
                "result_r",
                0.0,
            )
        )
        for trade in trades
        if trade["result"] == "WIN"
    )

    loss_r = abs(
        sum(
            float(
                trade.get(
                    "result_r",
                    0.0,
                )
            )
            for trade in trades
            if trade["result"] == "LOSS"
        )
    )

    profit_factor = (
        win_r / loss_r
        if loss_r > 0
        else 0.0
    )

    # ------------------------------------------------------
    # MAX DRAWDOWN
    # ------------------------------------------------------

    equity = 0.0

    peak = 0.0

    max_drawdown = 0.0

    for trade in trades:

        equity += float(
            trade.get(
                "result_r",
                0.0,
            )
        )

        if equity > peak:
            peak = equity

        drawdown = (
            peak - equity
        )

        if drawdown > max_drawdown:

            max_drawdown = (
                drawdown
            )

    # ------------------------------------------------------
    # WIN RATE
    # ------------------------------------------------------

    win_rate = (
        wins / closed * 100
        if closed
        else 0.0
    )

    return {

        "total": total,

        "closed": closed,

        "open": open_trades,

        "wins": wins,

        "losses": losses,

        "win_rate": win_rate,

        "total_r": total_r,

        "average_r": average_r,

        "profit_factor": profit_factor,

        "max_drawdown_r": max_drawdown,
    }


def print_backtest_report(
    trades,
    statistics,
):
    """
    Backtest natijasini terminalga chiqaradi.
    """

    print()

    print("=" * 70)

    print(
        "XAU_AI LIQUIDITY SWEEP BACKTEST"
    )

    print("=" * 70)

    print(
        f"TOTAL TRADES      : "
        f"{statistics['total']}"
    )

    print(
        f"CLOSED            : "
        f"{statistics['closed']}"
    )

    print(
        f"OPEN              : "
        f"{statistics['open']}"
    )

    print(
        f"WINS              : "
        f"{statistics['wins']}"
    )

    print(
        f"LOSSES            : "
        f"{statistics['losses']}"
    )

    print(
        f"WIN RATE          : "
        f"{statistics['win_rate']:.2f}%"
    )

    print(
        f"TOTAL R           : "
        f"{statistics['total_r']:.2f}"
    )

    print(
        f"AVERAGE R         : "
        f"{statistics['average_r']:.3f}"
    )

    print(
        f"PROFIT FACTOR     : "
        f"{statistics['profit_factor']:.3f}"
    )

    print(
        f"MAX DRAWDOWN      : "
        f"{statistics['max_drawdown_r']:.2f}R"
    )

    print("=" * 70)

    if not trades:

        print()

        print(
            "No trades found."
        )

        return

    print()

    print(
        "LAST TRADES"
    )

    print("-" * 70)

    for trade in trades[-10:]:

        print(
            f"{trade['signal_time']} | "
            f"{trade['direction']:4} | "
            f"{trade['result']:7} | "
            f"R={trade['result_r']:.2f} | "
            f"{trade['liquidity_sweep']}"
        )


def print_detailed_trade_statistics(
    trades,
):
    """
    BUY/SELL va sweep turi bo'yicha
    dastlabki statistikani chiqaradi.
    """

    if not trades:

        print()
        print(
            "No trades available for detailed statistics."
        )

        return

    print()

    print("=" * 70)

    print(
        "DETAILED TRADE STATISTICS"
    )

    print("=" * 70)

    # ------------------------------------------------------
    # BUY / SELL
    # ------------------------------------------------------

    for direction in (
        "BUY",
        "SELL",
    ):

        subset = [
            trade
            for trade in trades
            if trade["direction"]
            == direction
        ]

        if not subset:
            continue

        wins = sum(
            1
            for trade in subset
            if trade["result"]
            == "WIN"
        )

        losses = sum(
            1
            for trade in subset
            if trade["result"]
            == "LOSS"
        )

        closed = (
            wins + losses
        )

        total_r = sum(
            float(
                trade["result_r"]
            )
            for trade in subset
        )

        win_rate = (
            wins / closed * 100
            if closed
            else 0.0
        )

        print()

        print(
            f"{direction}"
        )

        print(
            f"  Trades   : {len(subset)}"
        )

        print(
            f"  Wins     : {wins}"
        )

        print(
            f"  Losses   : {losses}"
        )

        print(
            f"  Win Rate : {win_rate:.2f}%"
        )

        print(
            f"  Total R  : {total_r:.2f}"
        )

    # ------------------------------------------------------
    # SWEEP TYPE
    # ------------------------------------------------------

    for sweep in (
        "BULLISH_SWEEP",
        "BEARISH_SWEEP",
    ):

        subset = [
            trade
            for trade in trades
            if trade[
                "liquidity_sweep"
            ] == sweep
        ]

        if not subset:
            continue

        wins = sum(
            1
            for trade in subset
            if trade["result"]
            == "WIN"
        )

        losses = sum(
            1
            for trade in subset
            if trade["result"]
            == "LOSS"
        )

        closed = (
            wins + losses
        )

        total_r = sum(
            float(
                trade["result_r"]
            )
            for trade in subset
        )

        win_rate = (
            wins / closed * 100
            if closed
            else 0.0
        )

        print()

        print(
            sweep
        )

        print(
            f"  Trades   : {len(subset)}"
        )

        print(
            f"  Wins     : {wins}"
        )

        print(
            f"  Losses   : {losses}"
        )

        print(
            f"  Win Rate : {win_rate:.2f}%"
        )

        print(
            f"  Total R  : {total_r:.2f}"
        )

    print()

    print("=" * 70)


if __name__ == "__main__":

    print("=" * 70)

    print(
        "XAU_AI LIQUIDITY SWEEP BACKTEST ENGINE"
    )

    print("=" * 70)

    print()

    print(
        "Loading 5M historical candles..."
    )

    try:

        from data.market_data import (
            get_xauusd_candles
        )

        df = get_xauusd_candles(
            interval="5m",
            limit=1000,
        )

    except Exception as exc:

        print()

        print(
            f"ERROR loading market data: {exc}"
        )

        raise SystemExit(1)

    if df is None or df.empty:

        print()

        print(
            "ERROR: Market data yuklanmadi."
        )

        raise SystemExit(1)

    print(
        f"Loaded candles: {len(df)}"
    )

    print()

    print(
        "Running backtest..."
    )

    try:

        trades = (
            run_liquidity_sweep_backtest(
                df
            )
        )

    except Exception as exc:

        print()

        print(
            "BACKTEST ERROR:"
        )

        print(
            exc
        )

        raise SystemExit(1)

    statistics = (
        calculate_backtest_statistics(
            trades
        )
    )

    print_backtest_report(
        trades,
        statistics,
    )

    print_detailed_trade_statistics(
        trades
    )

    print()

    print(
        "BACKTEST FINISHED"
    )