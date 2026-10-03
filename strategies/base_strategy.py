from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StrategyResult:
    """
    Universal result model for all XAU_AI strategies.

    Har bir strategiya bir xil formatda natija qaytaradi.
    Keyinchalik Telegram, backtest va historical intelligence
    shu formatdan foydalanadi.
    """

    # ---------------------------------------------------------
    # STRATEGY INFORMATION
    # ---------------------------------------------------------

    strategy_id: str
    strategy_name: str
    strategy_version: str = "1.0"

    # ---------------------------------------------------------
    # MARKET INFORMATION
    # ---------------------------------------------------------

    analysis_time: Optional[str] = None
    symbol: str = "XAUUSD"
    timeframe: str = "5m"

    price: Optional[float] = None

    # ---------------------------------------------------------
    # SIGNAL
    # ---------------------------------------------------------

    signal: str = "NO_TRADE"
    setup: Optional[str] = None

    # ---------------------------------------------------------
    # TRADE LEVELS
    # ---------------------------------------------------------

    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None

    risk: Optional[float] = None
    rr_tp1: Optional[float] = None
    rr_tp2: Optional[float] = None

    # ---------------------------------------------------------
    # HTF CONTEXT
    # ---------------------------------------------------------

    trend_1d: Optional[str] = None
    trend_4h: Optional[str] = None
    trend_1h: Optional[str] = None
    trend_15m: Optional[str] = None
    trend_5m: Optional[str] = None

    htf_agreement: Optional[str] = None

    # ---------------------------------------------------------
    # INDICATORS
    # ---------------------------------------------------------

    indicators: Dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------
    # MARKET STRUCTURE
    # ---------------------------------------------------------

    structure: Dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------
    # LIQUIDITY / PRICE ACTION
    # ---------------------------------------------------------

    liquidity: Dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------
    # CONFIRMATIONS
    # ---------------------------------------------------------

    confirmations: List[str] = field(default_factory=list)

    confirmation_count: int = 0

    # ---------------------------------------------------------
    # REASONS
    # ---------------------------------------------------------

    reasons: List[str] = field(default_factory=list)

    # ---------------------------------------------------------
    # HISTORICAL INFORMATION
    # ---------------------------------------------------------

    historical_stats: Dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------
    # STATUS
    # ---------------------------------------------------------

    status: str = "READY"

    # ---------------------------------------------------------
    # EXTRA DATA
    # ---------------------------------------------------------

    metadata: Dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------
    # METHODS
    # ---------------------------------------------------------

    def add_confirmation(self, confirmation: str):
        """Add one confirmation to the result."""
        self.confirmations.append(confirmation)
        self.confirmation_count = len(self.confirmations)

    def add_reason(self, reason: str):
        """Add an explanation/reason."""
        self.reasons.append(reason)

    def is_trade(self) -> bool:
        """Return True if the strategy produced BUY or SELL."""
        return self.signal in ("BUY", "SELL")

    def is_no_trade(self) -> bool:
        """Return True if there is no valid trade."""
        return self.signal == "NO_TRADE"

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to a normal dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "strategy_version": self.strategy_version,

            "analysis_time": self.analysis_time,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "price": self.price,

            "signal": self.signal,
            "setup": self.setup,

            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "tp1": self.tp1,
            "tp2": self.tp2,

            "risk": self.risk,
            "rr_tp1": self.rr_tp1,
            "rr_tp2": self.rr_tp2,

            "trend_1d": self.trend_1d,
            "trend_4h": self.trend_4h,
            "trend_1h": self.trend_1h,
            "trend_15m": self.trend_15m,
            "trend_5m": self.trend_5m,

            "htf_agreement": self.htf_agreement,

            "indicators": self.indicators,
            "structure": self.structure,
            "liquidity": self.liquidity,

            "confirmations": self.confirmations,
            "confirmation_count": self.confirmation_count,

            "reasons": self.reasons,

            "historical_stats": self.historical_stats,

            "status": self.status,

            "metadata": self.metadata,
        }

    def summary(self) -> str:
        """Short human-readable strategy summary."""

        lines = [
            f"Strategy: {self.strategy_name}",
            f"Signal: {self.signal}",
            f"Price: {self.price}",
        ]

        if self.entry is not None:
            lines.append(f"Entry: {self.entry}")

        if self.stop_loss is not None:
            lines.append(f"SL: {self.stop_loss}")

        if self.tp1 is not None:
            lines.append(f"TP1: {self.tp1}")

        if self.tp2 is not None:
            lines.append(f"TP2: {self.tp2}")

        if self.risk is not None:
            lines.append(f"Risk: {self.risk}")

        if self.rr_tp1 is not None:
            lines.append(f"RR TP1: {self.rr_tp1}")

        if self.rr_tp2 is not None:
            lines.append(f"RR TP2: {self.rr_tp2}")

        lines.append(
            f"Confirmations: {self.confirmation_count}"
        )

        return "\n".join(lines)


class BaseStrategy:
    """
    Base class for all XAU_AI strategies.

    Har bir yangi strategiya shu klassdan meros oladi.
    """

    strategy_id = "base"
    strategy_name = "Base Strategy"
    strategy_version = "1.0"

    def analyze(self, *args, **kwargs) -> StrategyResult:
        """
        Har bir real strategiya o'z analyze() metodini implement qiladi.
        """
        raise NotImplementedError(
            "Strategy must implement analyze()"
        )

    def get_info(self) -> Dict[str, str]:
        """Return basic strategy information."""
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "strategy_version": self.strategy_version,
        }