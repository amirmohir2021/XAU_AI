"""
XAU_AI HISTORICAL OUTCOME ENGINE V6

Purpose:
    Evaluate historical research setups using ONLY future 5M candles.

Important:
    - No lookahead in setup evaluation.
    - Entry/SL/TP rules follow analysis/scalping_levels.py.
    - Future candles are used only after the signal candle.
    - If SL and TP are both touched inside the same candle,
      outcome is marked AMBIGUOUS because OHLC does not reveal
      intrabar order.

Input:
    data/historical/historical_research_v5.csv
    data/historical/XAUUSD_5m.csv

Output:
    data/historical/historical_outcomes_v6.csv
"""

from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RESEARCH_FILE = (
    BASE_DIR
    / "data"
    / "historical"
    / "historical_research_v5.csv"
)

HISTORICAL_5M_FILE = (
    BASE_DIR
    / "data"
    / "historical"
    / "XAUUSD_5m.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "historical"
    / "historical_outcomes_v6.csv"
)


# ============================================================
# SETTINGS
# ============================================================

TP1_RR = 1.5
TP2_RR = 2.5

ATR_SL_MULTIPLIER = 1.20
SWEEP_BUFFER_ATR = 0.15

MIN_RISK = 0.50

# Maximum number of future 5M candles to inspect.
# 0 = until the end of the historical dataset.
MAX_FUTURE_CANDLES = 0


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=None):
    try:
        if value is None:
            return default

        result = float(value)

        if pd.isna(result):
            return default

        return result

    except (TypeError, ValueError):
        return default


def normalize_direction(direction):
    if direction is None:
        return "NONE"

    direction = str(direction).upper().strip()

    if direction in ("BUY", "BULLISH", "LONG"):
        return "BUY"

    if direction in ("SELL", "BEARISH", "SHORT"):
        return "SELL"

    return "NONE"


def normalize_timestamp(value):
    return pd.to_datetime(value, utc=True)


# ============================================================
# LOAD DATA
# ============================================================

def load_research():
    if not RESEARCH_FILE.exists():
        raise FileNotFoundError(
            f"Research file not found:\n{RESEARCH_FILE}"
        )

    df = pd.read_csv(RESEARCH_FILE)

    required = {
        "timestamp",
        "price",
        "liquidity_sweep",
        "direction_5m",
        "setup",
        "1d",
        "4h",
        "1h",
        "15m",
        "atr_5m",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Research file missing columns: {sorted(missing)}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
    )

    df = df.sort_values("timestamp").reset_index(drop=True)

    return df


def load_5m_history():
    if not HISTORICAL_5M_FILE.exists():
        raise FileNotFoundError(
            f"Historical 5M file not found:\n"
            f"{HISTORICAL_5M_FILE}"
        )

    df = pd.read_csv(HISTORICAL_5M_FILE)

    required = {
        "datetime",
        "open",
        "high",
        "low",
        "close",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Historical 5M file missing columns: "
            f"{sorted(missing)}"
        )

    df["datetime"] = pd.to_datetime(
        df["datetime"],
        utc=True,
    )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = (
        df.dropna(
            subset=[
                "datetime",
                "open",
                "high",
                "low",
                "close",
            ]
        )
        .sort_values("datetime")
        .drop_duplicates(
            subset=["datetime"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    return df


# ============================================================
# STRUCTURAL LEVELS
# ============================================================

def get_recent_high(df_5m, signal_time, lookback=20):
    """
    Use only candles BEFORE the signal candle.

    This deliberately excludes the signal candle itself.
    """

    history = df_5m[
        df_5m["datetime"] < signal_time
    ].tail(lookback)

    if history.empty:
        return None

    return safe_float(history["high"].max())


def get_recent_low(df_5m, signal_time, lookback=20):
    """
    Use only candles BEFORE the signal candle.

    This deliberately excludes the signal candle itself.
    """

    history = df_5m[
        df_5m["datetime"] < signal_time
    ].tail(lookback)

    if history.empty:
        return None

    return safe_float(history["low"].min())


# ============================================================
# SL CALCULATION
# ============================================================

def calculate_stop_loss(
    direction,
    entry,
    atr,
    df_5m,
    signal_time,
    liquidity_sweep,
):
    direction = normalize_direction(direction)

    entry = safe_float(entry)
    atr = safe_float(atr)

    if direction == "NONE":
        return None, None, "INVALID_DIRECTION"

    if entry is None or entry <= 0:
        return None, None, "INVALID_ENTRY"

    if atr is None or atr <= 0:
        return None, None, "INVALID_ATR"

    minimum_risk = max(
        MIN_RISK,
        atr * 0.50,
    )

    atr_risk = max(
        atr * ATR_SL_MULTIPLIER,
        minimum_risk,
    )

    # --------------------------------------------------------
    # SELL
    # --------------------------------------------------------

    if direction == "SELL":

        atr_sl = entry + atr_risk

        recent_high = get_recent_high(
            df_5m,
            signal_time,
        )

        structural_sl = None

        if recent_high is not None:
            structural_sl = (
                recent_high
                + atr * SWEEP_BUFFER_ATR
            )

        if (
            liquidity_sweep == "BEARISH_SWEEP"
            and structural_sl is not None
        ):
            candidates = [
                atr_sl,
                structural_sl,
            ]

            valid_candidates = [
                level
                for level in candidates
                if level > entry + minimum_risk
            ]

            if valid_candidates:
                stop_loss = min(
                    valid_candidates
                )

                method = (
                    "ATR + BEARISH_SWEEP"
                )

            else:
                stop_loss = atr_sl
                method = "ATR"

        else:
            stop_loss = atr_sl
            method = "ATR"

        risk = stop_loss - entry

        return (
            round(stop_loss, 3),
            round(risk, 3),
            method,
        )

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    if direction == "BUY":

        atr_sl = entry - atr_risk

        recent_low = get_recent_low(
            df_5m,
            signal_time,
        )

        structural_sl = None

        if recent_low is not None:
            structural_sl = (
                recent_low
                - atr * SWEEP_BUFFER_ATR
            )

        if (
            liquidity_sweep == "BULLISH_SWEEP"
            and structural_sl is not None
        ):
            candidates = [
                atr_sl,
                structural_sl,
            ]

            valid_candidates = [
                level
                for level in candidates
                if level < entry - minimum_risk
            ]

            if valid_candidates:
                stop_loss = max(
                    valid_candidates
                )

                method = (
                    "ATR + BULLISH_SWEEP"
                )

            else:
                stop_loss = atr_sl
                method = "ATR"

        else:
            stop_loss = atr_sl
            method = "ATR"

        risk = entry - stop_loss

        return (
            round(stop_loss, 3),
            round(risk, 3),
            method,
        )

    return None, None, "INVALID_DIRECTION"


# ============================================================
# TAKE PROFITS
# ============================================================

def calculate_take_profits(
    direction,
    entry,
    risk,
):
    direction = normalize_direction(direction)

    if (
        direction == "NONE"
        or entry is None
        or risk is None
        or entry <= 0
        or risk <= 0
    ):
        return None, None

    if direction == "BUY":
        tp1 = entry + risk * TP1_RR
        tp2 = entry + risk * TP2_RR

    elif direction == "SELL":
        tp1 = entry - risk * TP1_RR
        tp2 = entry - risk * TP2_RR

    else:
        return None, None

    return (
        round(tp1, 3),
        round(tp2, 3),
    )


# ============================================================
# OUTCOME
# ============================================================

def evaluate_future(
    future_candles,
    direction,
    entry,
    stop_loss,
    tp1,
    tp2,
    risk,
):
    """
    Evaluate future candles only.

    Important:
        A candle can touch both SL and TP.

        OHLC does not tell us which level was hit first.

        Therefore:
            both SL + TP1 -> AMBIGUOUS
            both SL + TP2 -> AMBIGUOUS
            TP1 + TP2      -> TP2_FIRST
    """

    direction = normalize_direction(direction)

    max_mfe = 0.0
    max_mae = 0.0

    candles_checked = 0

    for _, candle in future_candles.iterrows():

        candles_checked += 1

        high = safe_float(candle["high"])
        low = safe_float(candle["low"])
        close = safe_float(candle["close"])

        if (
            high is None
            or low is None
            or close is None
        ):
            continue

        # ----------------------------------------------------
        # MFE / MAE
        # ----------------------------------------------------

        if direction == "BUY":

            favorable = high - entry
            adverse = entry - low

        elif direction == "SELL":

            favorable = entry - low
            adverse = high - entry

        else:
            continue

        if favorable > max_mfe:
            max_mfe = favorable

        if adverse > max_mae:
            max_mae = adverse

        # ----------------------------------------------------
        # BUY
        # ----------------------------------------------------

        if direction == "BUY":

            sl_hit = low <= stop_loss
            tp1_hit = high >= tp1
            tp2_hit = high >= tp2

            # Both directions touched in same candle.
            if sl_hit and (tp1_hit or tp2_hit):
                return {
                    "outcome": "AMBIGUOUS",
                    "exit_time": candle["datetime"],
                    "exit_price": None,
                    "r_result": None,
                    "candles_checked": candles_checked,
                    "mfe_price": max_mfe,
                    "mae_price": max_mae,
                }

            if sl_hit:
                return {
                    "outcome": "SL_FIRST",
                    "exit_time": candle["datetime"],
                    "exit_price": stop_loss,
                    "r_result": -1.0,
                    "candles_checked": candles_checked,
                    "mfe_price": max_mfe,
                    "mae_price": max_mae,
                }

            if tp2_hit:
                return {
                    "outcome": "TP2_FIRST",
                    "exit_time": candle["datetime"],
                    "exit_price": tp2,
                    "r_result": TP2_RR,
                    "candles_checked": candles_checked,
                    "mfe_price": max_mfe,
                    "mae_price": max_mae,
                }

            if tp1_hit:
                return {
                    "outcome": "TP1_FIRST",
                    "exit_time": candle["datetime"],
                    "exit_price": tp1,
                    "r_result": TP1_RR,
                    "candles_checked": candles_checked,
                    "mfe_price": max_mfe,
                    "mae_price": max_mae,
                }

        # ----------------------------------------------------
        # SELL
        # ----------------------------------------------------

        elif direction == "SELL":

            sl_hit = high >= stop_loss
            tp1_hit = low <= tp1
            tp2_hit = low <= tp2

            # Both directions touched in same candle.
            if sl_hit and (tp1_hit or tp2_hit):
                return {
                    "outcome": "AMBIGUOUS",
                    "exit_time": candle["datetime"],
                    "exit_price": None,
                    "r_result": None,
                    "candles_checked": candles_checked,
                    "mfe_price": max_mfe,
                    "mae_price": max_mae,
                }

            if sl_hit:
                return {
                    "outcome": "SL_FIRST",
                    "exit_time": candle["datetime"],
                    "exit_price": stop_loss,
                    "r_result": -1.0,
                    "candles_checked": candles_checked,
                    "mfe_price": max_mfe,
                    "mae_price": max_mae,
                }

            if tp2_hit:
                return {
                    "outcome": "TP2_FIRST",
                    "exit_time": candle["datetime"],
                    "exit_price": tp2,
                    "r_result": TP2_RR,
                    "candles_checked": candles_checked,
                    "mfe_price": max_mfe,
                    "mae_price": max_mae,
                }

            if tp1_hit:
                return {
                    "outcome": "TP1_FIRST",
                    "exit_time": candle["datetime"],
                    "exit_price": tp1,
                    "r_result": TP1_RR,
                    "candles_checked": candles_checked,
                    "mfe_price": max_mfe,
                    "mae_price": max_mae,
                }

    return {
        "outcome": "OPEN",
        "exit_time": None,
        "exit_price": None,
        "r_result": None,
        "candles_checked": candles_checked,
        "mfe_price": max_mfe,
        "mae_price": max_mae,
    }


# ============================================================
# SINGLE SETUP
# ============================================================

def evaluate_setup(
    setup_row,
    df_5m,
):
    signal_time = normalize_timestamp(
        setup_row["timestamp"]
    )

    price = safe_float(
        setup_row["price"]
    )

    atr = safe_float(
        setup_row["atr_5m"]
    )

    liquidity_sweep = str(
        setup_row["liquidity_sweep"]
    ).upper().strip()

    setup_type = str(
        setup_row["setup"]
    ).upper().strip()

    direction_5m = normalize_direction(
        setup_row["direction_5m"]
    )

    # --------------------------------------------------------
    # Only setups with actual BUY/SELL direction
    # --------------------------------------------------------

    if direction_5m not in ("BUY", "SELL"):

        return {
            **setup_row.to_dict(),
            "entry": price,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "risk": None,
            "sl_method": None,
            "outcome": "NO_TRADE",
            "exit_time": None,
            "exit_price": None,
            "r_result": None,
            "candles_checked": 0,
            "mfe_price": None,
            "mae_price": None,
        }

    # --------------------------------------------------------
    # Entry
    # --------------------------------------------------------

    entry = price

    if entry is None or entry <= 0:
        return {
            **setup_row.to_dict(),
            "entry": None,
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "risk": None,
            "sl_method": None,
            "outcome": "INVALID_SETUP",
            "exit_time": None,
            "exit_price": None,
            "r_result": None,
            "candles_checked": 0,
            "mfe_price": None,
            "mae_price": None,
        }

    # --------------------------------------------------------
    # SL
    # --------------------------------------------------------

    stop_loss, risk, sl_method = calculate_stop_loss(
        direction=direction_5m,
        entry=entry,
        atr=atr,
        df_5m=df_5m,
        signal_time=signal_time,
        liquidity_sweep=liquidity_sweep,
    )

    if (
        stop_loss is None
        or risk is None
        or risk <= 0
    ):
        return {
            **setup_row.to_dict(),
            "entry": round(entry, 3),
            "stop_loss": stop_loss,
            "tp1": None,
            "tp2": None,
            "risk": risk,
            "sl_method": sl_method,
            "outcome": "INVALID_SL",
            "exit_time": None,
            "exit_price": None,
            "r_result": None,
            "candles_checked": 0,
            "mfe_price": None,
            "mae_price": None,
        }

    # --------------------------------------------------------
    # TP
    # --------------------------------------------------------

    tp1, tp2 = calculate_take_profits(
        direction=direction_5m,
        entry=entry,
        risk=risk,
    )

    if tp1 is None or tp2 is None:
        return {
            **setup_row.to_dict(),
            "entry": round(entry, 3),
            "stop_loss": round(stop_loss, 3),
            "tp1": None,
            "tp2": None,
            "risk": round(risk, 3),
            "sl_method": sl_method,
            "outcome": "INVALID_TP",
            "exit_time": None,
            "exit_price": None,
            "r_result": None,
            "candles_checked": 0,
            "mfe_price": None,
            "mae_price": None,
        }

    # --------------------------------------------------------
    # FUTURE CANDLES ONLY
    # --------------------------------------------------------

    future = df_5m[
        df_5m["datetime"] > signal_time
    ]

    if MAX_FUTURE_CANDLES > 0:
        future = future.head(
            MAX_FUTURE_CANDLES
        )

    outcome = evaluate_future(
        future_candles=future,
        direction=direction_5m,
        entry=entry,
        stop_loss=stop_loss,
        tp1=tp1,
        tp2=tp2,
        risk=risk,
    )

    return {
        **setup_row.to_dict(),

        "entry": round(entry, 3),
        "stop_loss": round(stop_loss, 3),
        "tp1": round(tp1, 3),
        "tp2": round(tp2, 3),
        "risk": round(risk, 3),
        "sl_method": sl_method,

        **outcome,
    }


# ============================================================
# MAIN ENGINE
# ============================================================

def run():
    print("=" * 70)
    print("XAU_AI HISTORICAL OUTCOME ENGINE V6")
    print("=" * 70)
    print()

    print("Loading research data...")

    research = load_research()

    print(
        f"Research rows : {len(research)}"
    )

    print()
    print("Loading historical 5M data...")

    df_5m = load_5m_history()

    print(
        f"5M candles    : {len(df_5m)}"
    )

    print(
        f"5M first      : {df_5m['datetime'].iloc[0]}"
    )

    print(
        f"5M last       : {df_5m['datetime'].iloc[-1]}"
    )

    print()

    # --------------------------------------------------------
    # Important coverage check
    # --------------------------------------------------------

    research_start = research["timestamp"].min()
    research_end = research["timestamp"].max()

    history_start = df_5m["datetime"].min()
    history_end = df_5m["datetime"].max()

    print("Coverage:")
    print(
        f"Research : {research_start} -> {research_end}"
    )
    print(
        f"5M data  : {history_start} -> {history_end}"
    )

    print()

    if research_end > history_end:
        print(
            "WARNING: Some research setups occur "
            "after the end of the historical 5M dataset."
        )

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------

    results = []

    total = len(research)

    print(
        f"Evaluating {total} historical points..."
    )
    print()

    for index, row in research.iterrows():

        result = evaluate_setup(
            setup_row=row,
            df_5m=df_5m,
        )

        results.append(result)

        if (index + 1) % 1000 == 0:
            print(
                f"Processed: {index + 1}/{total}"
            )

    results_df = pd.DataFrame(results)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("=" * 70)
    print("OUTCOME SUMMARY")
    print("=" * 70)

    print()
    print(
        results_df["outcome"]
        .value_counts()
        .to_string()
    )

    print()
    print("SETUP DISTRIBUTION")
    print(
        results_df["setup"]
        .value_counts()
        .to_string()
    )

    print()
    print("DIRECTION")
    print(
        results_df["direction_5m"]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Trade-only statistics
    # --------------------------------------------------------

    trade_results = results_df[
        results_df["outcome"].isin(
            [
                "SL_FIRST",
                "TP1_FIRST",
                "TP2_FIRST",
                "AMBIGUOUS",
                "OPEN",
            ]
        )
    ]

    print()
    print("TRADE OUTCOMES")

    if trade_results.empty:
        print("No trade outcomes found.")

    else:
        print(
            trade_results["outcome"]
            .value_counts()
            .to_string()
        )

    # --------------------------------------------------------
    # Resolved R
    # --------------------------------------------------------

    resolved = results_df[
        results_df["r_result"].notna()
    ]

    if not resolved.empty:

        total_r = resolved["r_result"].sum()

        average_r = resolved["r_result"].mean()

        wins = resolved[
            resolved["r_result"] > 0
        ]

        losses = resolved[
            resolved["r_result"] < 0
        ]

        print()
        print("R STATISTICS")
        print(
            f"Resolved trades : {len(resolved)}"
        )
        print(
            f"Wins            : {len(wins)}"
        )
        print(
            f"Losses          : {len(losses)}"
        )
        print(
            f"Total R         : {total_r:.3f}"
        )
        print(
            f"Average R       : {average_r:.3f}"
        )

        if len(resolved) > 0:
            print(
                f"Win rate        : "
                f"{len(wins) / len(resolved) * 100:.2f}%"
            )

    print()
    print("Results saved:")
    print(OUTPUT_FILE)

    print()
    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run()