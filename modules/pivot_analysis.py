"""
Pivot Point Analysis Module
Calculates Classic, Fibonacci, and Camarilla pivot points.
Generates trading signals based on pivot levels.
"""
import pandas as pd
import numpy as np


class PivotAnalyzer:
    """Calculates pivot points and generates pivot-based trading signals."""

    def calculate_pivots(self, high: float, low: float, close: float) -> dict:
        """Calculate classic pivot points from previous day's HLC."""
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        s1 = (2 * pivot) - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)

        return {
            "pivot": round(pivot, 2),
            "r1": round(r1, 2),
            "r2": round(r2, 2),
            "r3": round(r3, 2),
            "s1": round(s1, 2),
            "s2": round(s2, 2),
            "s3": round(s3, 2),
        }

    def calculate_fibonacci_pivots(self, high: float, low: float, close: float) -> dict:
        """Calculate Fibonacci pivot points."""
        pivot = (high + low + close) / 3
        diff = high - low
        return {
            "pivot": round(pivot, 2),
            "r1": round(pivot + 0.382 * diff, 2),
            "r2": round(pivot + 0.618 * diff, 2),
            "r3": round(pivot + 1.0 * diff, 2),
            "s1": round(pivot - 0.382 * diff, 2),
            "s2": round(pivot - 0.618 * diff, 2),
            "s3": round(pivot - 1.0 * diff, 2),
        }

    def calculate_camarilla_pivots(self, high: float, low: float, close: float) -> dict:
        """Calculate Camarilla pivot points."""
        diff = high - low
        return {
            "pivot": round((high + low + close) / 3, 2),
            "r1": round(close + diff * 1.1 / 12, 2),
            "r2": round(close + diff * 1.1 / 6, 2),
            "r3": round(close + diff * 1.1 / 4, 2),
            "r4": round(close + diff * 1.1 / 2, 2),
            "s1": round(close - diff * 1.1 / 12, 2),
            "s2": round(close - diff * 1.1 / 6, 2),
            "s3": round(close - diff * 1.1 / 4, 2),
            "s4": round(close - diff * 1.1 / 2, 2),
        }

    def get_pivot_signal(self, current_price: float, pivots: dict,
                         rsi: float = 50, macd_bullish: bool = True) -> dict:
        """Generate trading signal based on pivot position."""
        pivot = pivots["pivot"]
        score = 0
        reasons = []

        if current_price > pivots["r2"]:
            score += 3
            reasons.append(f"Price above R2 ({pivots['r2']}) - Strong bullish")
        elif current_price > pivots["r1"]:
            score += 2
            reasons.append(f"Price above R1 ({pivots['r1']}) - Bullish")
        elif current_price > pivot:
            score += 1
            reasons.append(f"Price above Pivot ({pivot}) - Mild bullish")
        elif current_price < pivots["s2"]:
            score -= 3
            reasons.append(f"Price below S2 ({pivots['s2']}) - Strong bearish")
        elif current_price < pivots["s1"]:
            score -= 2
            reasons.append(f"Price below S1 ({pivots['s1']}) - Bearish")
        elif current_price < pivot:
            score -= 1
            reasons.append(f"Price below Pivot ({pivot}) - Mild bearish")

        if rsi > 50:
            score += 1
            reasons.append(f"RSI {rsi:.0f} > 50 (Bullish)")
        else:
            score -= 1
            reasons.append(f"RSI {rsi:.0f} < 50 (Bearish)")

        if macd_bullish:
            score += 1
            reasons.append("MACD Bullish")
        else:
            score -= 1
            reasons.append("MACD Bearish")

        if score >= 4:
            signal = "STRONG BUY"
        elif score >= 2:
            signal = "BUY"
        elif score <= -4:
            signal = "STRONG SELL"
        elif score <= -2:
            signal = "SELL"
        else:
            signal = "HOLD"

        return {
            "signal": signal,
            "score": score,
            "price_vs_pivot": "Above" if current_price > pivot else "Below",
            "nearest_support": pivots["s1"] if current_price > pivot else pivots["s2"],
            "nearest_resistance": pivots["r1"] if current_price < pivots["r1"] else pivots["r2"],
            "reasons": reasons,
        }
