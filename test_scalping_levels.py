from memory.history import get_5m_candles
from analysis.scalping_5m import analyze_5m
from analysis.scalping_levels import (
    generate_scalping_levels,
    format_scalping_levels,
)


def main():

    print("=" * 70)
    print("XAU/USD 5M ENTRY / SL / TP TEST")
    print("=" * 70)

    # ========================================================
    # 1. Load 5M history from SQLite
    # ========================================================

    df = get_5m_candles(limit=500)

    if df.empty:
        print("ERROR: 5M candles not found.")
        return

    print(f"Loaded 5M candles: {len(df)}")

    print(
        f"Period: {df['open_time'].iloc[0]} -> "
        f"{df['open_time'].iloc[-1]}"
    )

    # ========================================================
    # 2. Run 5M analysis
    # ========================================================

    analysis = analyze_5m(df)

    print()
    print("-" * 70)
    print("5M ANALYSIS")
    print("-" * 70)

    print(
        f"Direction : {analysis.get('direction')}"
    )

    print(
        f"Strength  : {analysis.get('strength')}"
    )

    print(
        f"Setup     : {analysis.get('setup')}"
    )

    print(
        f"ATR       : {analysis.get('atr')}"
    )

    print(
        f"RSI       : {analysis.get('rsi')}"
    )

    print(
        f"ADX       : {analysis.get('adx')}"
    )

    print(
        f"Liquidity : {analysis.get('liquidity_sweep')}"
    )

    # ========================================================
    # 3. Generate Entry / SL / TP
    # ========================================================

    levels = generate_scalping_levels(
        df=df,
        analysis_result=analysis
    )

    print()

    print(
        format_scalping_levels(levels)
    )

    # ========================================================
    # 4. Finish
    # ========================================================

    print()
    print("=" * 70)
    print("ENTRY / SL / TP TEST FINISHED")
    print("=" * 70)


if __name__ == "__main__":
    main()
