from pathlib import Path
import sys
from typing import Any, Dict, Optional


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORTS
# ============================================================

from data.market_data import get_xauusd_candles
from analysis.indicators import (
    calculate_indicators,
    get_latest_indicator_values,
)
from analysis.structure import analyze_structure
from analysis.signal_engine import generate_signal


# ============================================================
# SETTINGS
# ============================================================

TIMEFRAMES = {
    "1d": "1d",
    "4h": "4h",
    "1h": "1h",
    "15m": "15m",
}

CANDLE_LIMIT = 250
STRUCTURE_CANDLE_LIMIT = 300


# ============================================================
# HTF CONTEXT ADAPTER
# ============================================================

class HTFContextAdapter:
    """
    V3.1 signal engine uchun HTF ma'lumotlarini tayyorlaydi
    va V3.1 natijasini strategiyalar uchun universal context
    formatiga aylantiradi.

    Muhim:

        Bu class V3.1 logikasini qayta yozmaydi.

        Asosiy signal qarori hali ham:

            analysis.signal_engine.generate_signal()

        orqali olinadi.

    Adapter vazifasi:

        Market data
            ↓
        Indicators
            ↓
        4H Structure
            ↓
        V3.1 Signal Engine
            ↓
        Universal HTF Context
    """

    # ========================================================
    # MAIN
    # ========================================================

    def build(self) -> Dict[str, Any]:
        """
        XAU/USD uchun V3.1 HTF context yaratadi.

        Return:
            {
                "status": ...,
                "signal": ...,
                "direction": ...,
                ...
            }
        """

        timeframe_data = {}

        # ----------------------------------------------------
        # LOAD 1D / 4H / 1H / 15M
        # ----------------------------------------------------

        for name, interval in TIMEFRAMES.items():

            df = get_xauusd_candles(
                interval=interval,
                limit=CANDLE_LIMIT
            )

            if df is None or df.empty:

                return {
                    "status": "ERROR",
                    "message": (
                        f"{interval} timeframe uchun "
                        f"market data olinmadi."
                    ),
                }

            df = calculate_indicators(df)

            indicators = get_latest_indicator_values(df)

            timeframe_data[name] = indicators

        # ----------------------------------------------------
        # 4H STRUCTURE
        # ----------------------------------------------------

        structure_df = get_xauusd_candles(
            interval="4h",
            limit=STRUCTURE_CANDLE_LIMIT
        )

        if structure_df is None or structure_df.empty:

            return {
                "status": "ERROR",
                "message": (
                    "4H structure data olinmadi."
                ),
            }

        structure_result = analyze_structure(
            structure_df
        )

        # ----------------------------------------------------
        # V3.1
        # ----------------------------------------------------

        signal_result = generate_signal(
            timeframe_data=timeframe_data,
            structure_data=structure_result,
        )

        # ----------------------------------------------------
        # UNIVERSAL CONTEXT
        # ----------------------------------------------------

        context = self._build_context(
            signal_result=signal_result,
            timeframe_data=timeframe_data,
            structure_result=structure_result,
        )

        return context

    # ========================================================
    # CONTEXT BUILDER
    # ========================================================

    def _build_context(
        self,
        signal_result: Dict[str, Any],
        timeframe_data: Dict[str, Any],
        structure_result: Dict[str, Any],
    ) -> Dict[str, Any]:

        # ----------------------------------------------------
        # TIMEFRAME DIRECTIONS
        # ----------------------------------------------------

        trend_1d = signal_result.get(
            "major_direction"
        )

        trend_4h = signal_result.get(
            "structure_direction"
        )

        trend_1h = signal_result.get(
            "h1_direction"
        )

        trend_15m = signal_result.get(
            "m15_direction"
        )

        # ----------------------------------------------------
        # SIGNAL
        # ----------------------------------------------------

        signal = signal_result.get(
            "signal",
            "WAIT"
        )

        # ----------------------------------------------------
        # HTF AGREEMENT
        # ----------------------------------------------------

        htf_agreement = self._determine_htf_agreement(
            trend_1d=trend_1d,
            trend_4h=trend_4h,
            trend_1h=trend_1h,
            trend_15m=trend_15m,
        )

        # ----------------------------------------------------
        # RETURN
        # ----------------------------------------------------

        return {
            "status": "OK",

            # ----------------------------------------------
            # V3.1 RESULT
            # ----------------------------------------------

            "signal": signal,

            "price": signal_result.get(
                "price"
            ),

            "confidence": signal_result.get(
                "confidence"
            ),

            "confirmations": signal_result.get(
                "confirmations"
            ),

            "major_direction": trend_1d,

            "structure_direction": trend_4h,

            "h1_direction": trend_1h,

            "m15_direction": trend_15m,

            "market_phase": signal_result.get(
                "market_phase"
            ),

            "entry_trigger": signal_result.get(
                "entry_trigger"
            ),

            # ----------------------------------------------
            # HTF CONTEXT
            # ----------------------------------------------

            "1d": trend_1d,
            "4h": trend_4h,
            "1h": trend_1h,
            "15m": trend_15m,

            "htf_agreement": htf_agreement,

            # ----------------------------------------------
            # TRADE LEVELS FROM V3.1
            # ----------------------------------------------

            "entry": signal_result.get(
                "entry"
            ),

            "stop_loss": signal_result.get(
                "stop_loss"
            ),

            "tp1": signal_result.get(
                "tp1"
            ),

            "tp2": signal_result.get(
                "tp2"
            ),

            "risk": signal_result.get(
                "risk"
            ),

            # ----------------------------------------------
            # STRUCTURE LEVELS
            # ----------------------------------------------

            "support": signal_result.get(
                "support"
            ),

            "resistance": signal_result.get(
                "resistance"
            ),

            "recent_bos": signal_result.get(
                "recent_bos"
            ),

            "recent_choch": signal_result.get(
                "recent_choch"
            ),

            # ----------------------------------------------
            # REASONS
            # ----------------------------------------------

            "reasons": list(
                signal_result.get(
                    "reasons",
                    []
                )
            ),

            # ----------------------------------------------
            # RAW DATA
            # ----------------------------------------------

            "timeframe_data": timeframe_data,

            "structure_data": structure_result,
        }

    # ========================================================
    # HTF AGREEMENT
    # ========================================================

    @staticmethod
    def _determine_htf_agreement(
        trend_1d: Optional[str],
        trend_4h: Optional[str],
        trend_1h: Optional[str],
        trend_15m: Optional[str],
    ) -> str:

        trends = [
            trend_1d,
            trend_4h,
            trend_1h,
            trend_15m,
        ]

        valid = [
            str(value).upper()
            for value in trends
            if value is not None
        ]

        bullish = valid.count(
            "BULLISH"
        )

        bearish = valid.count(
            "BEARISH"
        )

        # ----------------------------------------------------
        # Strong agreement
        # ----------------------------------------------------

        if bullish >= 3:

            return "BULLISH"

        if bearish >= 3:

            return "BEARISH"

        # ----------------------------------------------------
        # Weak agreement
        # ----------------------------------------------------

        if bullish > bearish:

            return "WEAK_BULLISH"

        if bearish > bullish:

            return "WEAK_BEARISH"

        # ----------------------------------------------------
        # Mixed
        # ----------------------------------------------------

        return "MIXED"


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def get_htf_context() -> Dict[str, Any]:
    """
    V3.1 HTF context olish uchun oddiy helper.
    """

    adapter = HTFContextAdapter()

    return adapter.build()


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("XAU_AI HTF ADAPTER TEST")
    print("=" * 70)

    print()
    print("Loading V3.1 HTF context...")

    try:

        context = get_htf_context()

    except Exception as exc:

        print()
        print(
            f"[ERROR] "
            f"{type(exc).__name__}: {exc}"
        )

        raise

    print()

    if context.get("status") != "OK":

        print(
            "STATUS:",
            context.get("status")
        )

        print(
            "MESSAGE:",
            context.get("message")
        )

    else:

        print(
            "STATUS:",
            context.get("status")
        )

        print()
        print("V3.1 SIGNAL")
        print("-" * 40)

        print(
            "Signal          :",
            context.get("signal")
        )

        print(
            "Price           :",
            context.get("price")
        )

        print(
            "Confirmations   :",
            context.get("confirmations")
        )

        print(
            "Confidence      :",
            context.get("confidence")
        )

        print()
        print("TIMEFRAME DIRECTIONS")
        print("-" * 40)

        print(
            "1D              :",
            context.get("1d")
        )

        print(
            "4H              :",
            context.get("4h")
        )

        print(
            "1H              :",
            context.get("1h")
        )

        print(
            "15M             :",
            context.get("15m")
        )

        print()
        print(
            "HTF AGREEMENT   :",
            context.get("htf_agreement")
        )

        print()
        print("V3.1 DETAILS")
        print("-" * 40)

        print(
            "Market phase    :",
            context.get("market_phase")
        )

        print(
            "Entry trigger   :",
            context.get("entry_trigger")
        )

        print(
            "Support         :",
            context.get("support")
        )

        print(
            "Resistance      :",
            context.get("resistance")
        )

        print()
        print("REASONS")
        print("-" * 40)

        for reason in context.get(
            "reasons",
            []
        ):

            print(
                "-",
                reason
            )

    print()
    print("=" * 70)
    print("HTF ADAPTER TEST FINISHED")
    print("=" * 70)