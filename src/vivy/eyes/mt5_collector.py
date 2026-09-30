"""
MT5 Data Collector (Eyes) — Market Perception for ViVy AI Engine.
Collects real-time prices, technical indicators, account metrics, and active positions.
"""

from dataclasses import dataclass
import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Candle:
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class TechnicalIndicatorEngine:
    """Computes technical indicators natively."""

    @staticmethod
    def calculate_rsi(closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        gains, losses = 0.0, 0.0
        for i in range(1, period + 1):
            diff = closes[i] - closes[i - 1]
            if diff >= 0:
                gains += diff
            else:
                losses -= diff
        avg_gain = gains / period
        avg_loss = losses / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100.0 - (100.0 / (1.0 + rs)), 2)

    @staticmethod
    def calculate_ema(closes: List[float], period: int = 20) -> float:
        if not closes:
            return 0.0
        if len(closes) < period:
            return sum(closes) / len(closes)
        k = 2.0 / (period + 1)
        ema = closes[0]
        for price in closes[1:]:
            ema = (price * k) + (ema * (1.0 - k))
        return round(ema, 5)

    @staticmethod
    def calculate_atr(candles: List[Candle], period: int = 14) -> float:
        if len(candles) < period + 1:
            return 0.0
        tr_list = []
        for i in range(1, len(candles)):
            high = candles[i].high
            low = candles[i].low
            prev_close = candles[i - 1].close
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)
        return round(sum(tr_list[-period:]) / period, 5)


class MT5DataCollector:
    """Perception Layer (Eyes) for MT5 Terminal."""

    def __init__(self, symbol: str = "GOLD"):
        self.symbol = symbol

    def get_market_snapshot(
        self,
        candles: Optional[List[Candle]] = None,
        positions: Optional[List[Dict[str, Any]]] = None,
        account_balance: float = 10000.0
    ) -> Dict[str, Any]:
        """Assembles complete market context dictionary for ViVy."""

        # Generate fallback candle data if none provided
        if not candles:
            candles = [
                Candle(time=i, open=2380.0 + i*0.1, high=2385.0 + i*0.1, low=2378.0 + i*0.1, close=2383.0 + i*0.1, volume=100.0)
                for i in range(30)
            ]

        closes = [c.close for c in candles]
        current_price = closes[-1] if closes else 0.0

        rsi = TechnicalIndicatorEngine.calculate_rsi(closes)
        ema_20 = TechnicalIndicatorEngine.calculate_ema(closes, 20)
        ema_50 = TechnicalIndicatorEngine.calculate_ema(closes, 50)
        atr = TechnicalIndicatorEngine.calculate_atr(candles)

        return {
            "symbol": self.symbol,
            "current_price": current_price,
            "account_balance": account_balance,
            "indicators": {
                "rsi_14": rsi,
                "ema_20": ema_20,
                "ema_50": ema_50,
                "atr_14": atr,
                "trend": "BULLISH" if ema_20 > ema_50 else "BEARISH"
            },
            "active_positions": positions or [],
            "recent_candles_count": len(candles)
        }
