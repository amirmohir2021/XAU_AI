from __future__ import annotations

from datetime import datetime, timezone

from data.market_data import get_xauusd_candles
from strategies.htf_adapter import get_htf_context
from strategies.liquidity_sweep import LiquiditySweepStrategy
from memory.signal_logger import log_strategy_signal


SYMBOL = "XAUUSD"
TIMEFRAME = "5m"
CANDLE_LIMIT = 300


def load_5m_data():
    """
    Load latest 5M candles.

    Only closed candles are used for analysis.
    """

    df = get_xauusd_candles(
        interval=TIMEFRAME,
        limit=CANDLE_LIMIT,
    )

    if df is None or df.empty:
        raise RuntimeError("5M market data is empty.")

    # The market_data.py format uses camelCase.
    if "isOpen" in df.columns:
        df = df[df["isOpen"] == False].copy()

    if len(df) < 220:
        raise RuntimeError(
            f"Not enough closed 5M candles: {len(df)}"
        )

    return df.reset_index(drop=True)


def print_header():
    print()
    print("=" * 100)
    print("XAU_AI SIGNAL COLLECTOR")
    print("=" * 100)

    print(f"Symbol    : {SYMBOL}")
    print(f"Timeframe : {TIMEFRAME}")

    print(
        f"Analysis  : "
        f"{datetime.now(timezone.utc).isoformat()}"
    )

    print("=" * 100)


def print_htf_context(htf_context):
    print()
    print("-" * 100)
    print("HTF CONTEXT")
    print("-" * 100)

    print(
        f"V3.1 SIGNAL       : "
        f"{htf_context.get('signal', 'N/A')}"
    )

    print(
        f"V3.1 CONFIRMATIONS: "
        f"{htf_context.get('confirmations', 0)}"
    )

    print(
        f"V3.1 ALIGNMENT    : "
        f"{htf_context.get('confidence', 0)}"
    )

    print(
        f"1D                : "
        f"{htf_context.get('1d', 'N/A')}"
    )

    print(
        f"4H                : "
        f"{htf_context.get('4h', 'N/A')}"
    )

    print(
        f"1H                : "
        f"{htf_context.get('1h', 'N/A')}"
    )

    print(
        f"15M               : "
        f"{htf_context.get('15m', 'N/A')}"
    )

    print(
        f"HTF AGREEMENT     : "
        f"{htf_context.get('htf_agreement', 'N/A')}"
    )

    print(
        f"MARKET PHASE      : "
        f"{htf_context.get('market_phase', 'N/A')}"
    )

    print(
        f"ENTRY TRIGGER     : "
        f"{htf_context.get('entry_trigger', 'N/A')}"
    )


def print_strategy_result(result):
    print()
    print("-" * 100)
    print("STRATEGY RESULT")
    print("-" * 100)

    print(
        f"STRATEGY          : "
        f"{result.strategy_name}"
    )

    print(
        f"VERSION           : "
        f"{result.strategy_version}"
    )

    print(
        f"SIGNAL            : "
        f"{result.signal}"
    )

    print(
        f"SETUP             : "
        f"{result.setup}"
    )

    print(
        f"STATUS            : "
        f"{result.status}"
    )

    print(
        f"PRICE             : "
        f"{result.price}"
    )

    print(
        f"5M TREND          : "
        f"{result.trend_5m}"
    )

    print(
        f"CONFIRMATIONS     : "
        f"{result.confirmation_count}"
    )

    print(
        f"ENTRY             : "
        f"{result.entry}"
    )

    print(
        f"STOP LOSS         : "
        f"{result.stop_loss}"
    )

    print(
        f"TP1               : "
        f"{result.tp1}"
    )

    print(
        f"TP2               : "
        f"{result.tp2}"
    )

    print(
        f"RISK              : "
        f"{result.risk}"
    )

    print(
        f"RR TP1            : "
        f"{result.rr_tp1}"
    )

    print(
        f"RR TP2            : "
        f"{result.rr_tp2}"
    )


def save_signal_if_trade(result):
    """
    Save only BUY/SELL signals.

    NO_TRADE is never saved.
    """

    print()
    print("-" * 100)
    print("SIGNAL LOGGER")
    print("-" * 100)

    if result.signal not in {"BUY", "SELL"}:
        print("SIGNAL SAVED      : NO")
        print(
            "Reason            : "
            "Strategy returned NO_TRADE."
        )
        return None

    signal_id = log_strategy_signal(result)

    if signal_id is None:
        print("SIGNAL SAVED      : NO")
        return None

    result.metadata["signal_id"] = signal_id

    print("SIGNAL SAVED      : YES")
    print(
        f"SIGNAL ID         : "
        f"{signal_id}"
    )

    return signal_id


def collect_signal():
    """
    Run one complete XAU_AI signal collection cycle.

    Flow:

        5M market data
             ↓
        HTF context
             ↓
        Liquidity Sweep strategy
             ↓
        Final BUY/SELL
             ↓
        Signal Logger
    """

    print_header()

    # ---------------------------------------------------------
    # 1. LOAD 5M DATA
    # ---------------------------------------------------------

    print()
    print("Loading 5M market data...")

    df_5m = load_5m_data()

    print(
        f"Loaded closed 5M candles: "
        f"{len(df_5m)}"
    )

    latest_candle = df_5m.iloc[-1]

    latest_time = latest_candle["openTime"]
    latest_price = latest_candle["close"]

    print(
        f"Latest candle time : "
        f"{latest_time}"
    )

    print(
        f"Latest price       : "
        f"{latest_price}"
    )

    # ---------------------------------------------------------
    # 2. BUILD HTF CONTEXT
    # ---------------------------------------------------------

    print()
    print("Building HTF context...")

    htf_context = get_htf_context()

    print_htf_context(htf_context)

    # ---------------------------------------------------------
    # 3. RUN STRATEGY
    # ---------------------------------------------------------

    print()
    print("Running Liquidity Sweep strategy...")

    strategy = LiquiditySweepStrategy()

    result = strategy.analyze(
        df_5m=df_5m,
        htf_context=htf_context,
    )

    print_strategy_result(result)

    # ---------------------------------------------------------
    # 4. SAVE SIGNAL
    # ---------------------------------------------------------

    save_signal_if_trade(result)

    # ---------------------------------------------------------
    # 5. FINISH
    # ---------------------------------------------------------

    print()
    print("=" * 100)
    print("SIGNAL COLLECTION FINISHED")
    print("=" * 100)

    return result


if __name__ == "__main__":
    collect_signal()