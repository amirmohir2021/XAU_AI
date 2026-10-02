import pandas as pd
import strategy_lab.strategy_anakyzer as a
from data.market_data import get_xauusd_candles

df5 = a.prepare_dataframe(get_xauusd_candles(interval="5m", limit=1000))
df15 = a.prepare_dataframe(get_xauusd_candles(interval="15m", limit=1000))
df1 = a.prepare_dataframe(get_xauusd_candles(interval="1h", limit=1000))
df4 = a.prepare_dataframe(get_xauusd_candles(interval="4h", limit=1000))
dfD = a.prepare_dataframe(get_xauusd_candles(interval="1d", limit=1000))

print("DATA:")
print("5M :", len(df5))
print("15M:", len(df15))
print("1H :", len(df1))
print("4H :", len(df4))
print("1D :", len(dfD))

print()
print("=" * 70)

for i in [219, 250, 280]:

    history_5m = df5.iloc[:i + 1].copy()
    signal_time = pd.Timestamp(history_5m.iloc[-1]["openTime"])

    history_15m = a.historical_slice(df15, signal_time)
    history_1h = a.historical_slice(df1, signal_time)
    history_4h = a.historical_slice(df4, signal_time)
    history_1d = a.historical_slice(dfD, signal_time)

    context = a.build_v31_context(
        history_5m,
        history_15m,
        history_1h,
        history_4h,
        history_1d
    )

    print("TIME:", signal_time)
    print("5M candles:", len(history_5m))
    print("15M candles:", len(history_15m))
    print("1H candles:", len(history_1h))
    print("4H candles:", len(history_4h))
    print("1D candles:", len(history_1d))
    print()
    print("V31 SIGNAL     :", context.get("signal"))
    print("CONFIRMATIONS  :", context.get("confirmations"))
    print("ALIGNMENT      :", context.get("confidence"))
    print("MAJOR          :", context.get("major_direction"))
    print("STRUCTURE      :", context.get("structure_direction"))
    print("H1             :", context.get("h1_direction"))
    print("M15            :", context.get("m15_direction"))
    print("PHASE          :", context.get("market_phase"))
    print("TRIGGER        :", context.get("entry_trigger"))
    print("5M TREND       :", context.get("trend_5m"))
    print("HTF AGREEMENT  :", context.get("htf_agreement"))
    print("=" * 70)
