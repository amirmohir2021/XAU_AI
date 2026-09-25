from data.market_data import get_all_timeframes_for_analysis


print("=" * 70)
print("XAU_AI HISTORICAL DATA TEST")
print("=" * 70)

data = get_all_timeframes_for_analysis(
    required_bars=1000
)

print("\n" + "=" * 70)
print("NATIJALAR")
print("=" * 70)

for name, df in data.items():

    print(f"\n{name}")
    print("-" * 40)

    print("Candle soni:", len(df))

    if not df.empty:
        print("Birinchi:", df.iloc[0]["openTime"])
        print("Oxirgi  :", df.iloc[-1]["openTime"])

print("\n" + "=" * 70)
print("TEST YAKUNLANDI")
print("=" * 70)