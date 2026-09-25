from memory.history import get_5m_candles
from analysis.scalping_5m import analyze_5m, format_5m_analysis


def main():
    print("=" * 70)
    print("XAU/USD 5M SCALPING ENGINE TEST")
    print("=" * 70)

    # SQLite xotiradan 5M candlelarni olish
    df = get_5m_candles(limit=500)

    if df.empty:
        print("ERROR: 5M candle ma'lumotlari topilmadi.")
        return

    print(f"Loaded 5M candles: {len(df)}")
    print(
        f"Period: {df['open_time'].iloc[0]} -> "
        f"{df['open_time'].iloc[-1]}"
    )

    print()
    print("-" * 70)
    print("Running 5M analysis...")
    print("-" * 70)

    result = analyze_5m(df)

    print()
    print(format_5m_analysis(result))

    print()
    print("=" * 70)
    print("5M ENGINE TEST FINISHED")
    print("=" * 70)


if __name__ == "__main__":
    main()
