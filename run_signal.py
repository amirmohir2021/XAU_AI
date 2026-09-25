from data.market_data import get_xauusd_candles
from analysis.indicators import calculate_indicators, get_latest_indicator_values
from analysis.structure import analyze_structure
from analysis.signal_engine import generate_signal, format_signal


TIMEFRAMES = {
    "1d": "1d",
    "4h": "4h",
    "1h": "1h",
    "15m": "15m",
}


def load_timeframe(interval):
    print(f"Loading {interval}...")

    df = get_xauusd_candles(
        interval=interval,
        limit=250
    )

    if df is None or df.empty:
        raise RuntimeError(
            f"{interval} timeframe uchun market data olinmadi."
        )

    df = calculate_indicators(df)

    indicators = get_latest_indicator_values(df)

    return df, indicators


def main():

    print("=" * 70)
    print("XAU/USD REAL SIGNAL TEST")
    print("=" * 70)

    timeframe_data = {}

    # ========================================================
    # LOAD ALL TIMEFRAMES
    # ========================================================

    for name, interval in TIMEFRAMES.items():

        try:

            df, indicators = load_timeframe(interval)

            timeframe_data[name] = indicators

            print(
                f"{name.upper():5} -> "
                f"{len(df)} candles | "
                f"Price: {indicators.get('price', 0):.3f}"
            )

        except Exception as e:

            print(
                f"{name.upper():5} -> ERROR: {e}"
            )

    # ========================================================
    # 4H MARKET STRUCTURE
    # ========================================================

    print()
    print("-" * 70)
    print("Analyzing 4H market structure...")
    print("-" * 70)

    structure_df = get_xauusd_candles(
        interval="4h",
        limit=300
    )

    if structure_df is None or structure_df.empty:

        raise RuntimeError(
            "4H structure data olinmadi."
        )

    structure_result = analyze_structure(
        structure_df
    )

    print(
        f"Structure trend: "
        f"{structure_result.get('trend', 'NEUTRAL')}"
    )

    print(
        f"BOS: "
        f"{len(structure_result.get('bos', []))}"
    )

    print(
        f"CHOCH: "
        f"{len(structure_result.get('choch', []))}"
    )

    # ========================================================
    # GENERATE SIGNAL
    # ========================================================

    print()
    print("-" * 70)
    print("Generating signal...")
    print("-" * 70)

    result = generate_signal(
        timeframe_data=timeframe_data,
        structure_data=structure_result,
    )

    # ========================================================
    # PRINT RESULT
    # ========================================================

    print()
    print("=" * 70)
    print(format_signal(result))
    print("=" * 70)


if __name__ == "__main__":
    main()