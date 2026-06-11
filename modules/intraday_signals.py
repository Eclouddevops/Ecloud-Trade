"""
Intraday Trading Signals Module
Generates intraday entry/exit signals with targets and stop losses.
"""
import numpy as np


class IntradaySignalGenerator:
    """Generates intraday trading signals with entry, SL, and targets."""

    def generate_intraday_signal(self, symbol: str, current_price: float,
                                  pivots: dict, indicators: dict,
                                  volatility: dict = None) -> dict:
        """
        Generate complete intraday trade setup.

        Args:
            symbol: Stock/Index symbol
            current_price: Current market price
            pivots: Pivot point levels
            indicators: Technical indicator values
            volatility: Volatility data (ATR, expected move)
        """
        score = 0
        reasons = []
        pivot = pivots.get("pivot", current_price)

        # Price vs Pivot
        if current_price > pivot:
            score += 2
            reasons.append(f"Price above Pivot ({pivot})")
        else:
            score -= 2
            reasons.append(f"Price below Pivot ({pivot})")

        # Price vs VWAP (if available)
        vwap = indicators.get("vwap")
        if vwap:
            if current_price > vwap:
                score += 1.5
                reasons.append(f"Above VWAP ({vwap})")
            else:
                score -= 1.5
                reasons.append(f"Below VWAP ({vwap})")

        # RSI
        rsi = indicators.get("rsi", 50)
        if rsi > 55:
            score += 1
            reasons.append(f"RSI {rsi} bullish")
        elif rsi < 45:
            score -= 1
            reasons.append(f"RSI {rsi} bearish")

        # MACD
        macd_bull = "Bullish" in str(indicators.get("macd_crossover", ""))
        if macd_bull:
            score += 1.5
            reasons.append("MACD Bullish")
        else:
            score -= 1.5
            reasons.append("MACD Bearish")

        # Volume
        vol_ratio = indicators.get("volume_ratio", 1)
        if vol_ratio > 1.5:
            score += 1
            reasons.append(f"Volume spike {vol_ratio:.1f}x")

        # Determine direction
        if score >= 3:
            direction = "BUY"
            confidence = min(95, 60 + int(score * 5))
            entry = round(current_price, 2)
            sl = round(max(pivots.get("s1", pivots.get("support_1", current_price * 0.995)), current_price - (current_price * 0.005)), 2)
            t1 = round(pivots.get("r1", pivots.get("resistance_1", current_price * 1.005)), 2)
            t2 = round(pivots.get("r2", pivots.get("resistance_2", current_price * 1.01)), 2)
            t3 = round(pivots.get("r3", pivots.get("resistance_2", current_price * 1.015)) * 1.005, 2) if pivots.get("r3") else round(current_price * 1.015, 2)
        elif score <= -3:
            direction = "SELL"
            confidence = min(95, 60 + int(abs(score) * 5))
            entry = round(current_price, 2)
            sl = round(min(pivots.get("r1", pivots.get("resistance_1", current_price * 1.005)), current_price + (current_price * 0.005)), 2)
            t1 = round(pivots.get("s1", pivots.get("support_1", current_price * 0.995)), 2)
            t2 = round(pivots.get("s2", pivots.get("support_2", current_price * 0.99)), 2)
            t3 = round(pivots.get("s3", pivots.get("support_2", current_price * 0.985)) * 0.995, 2) if pivots.get("s3") else round(current_price * 0.985, 2)
        else:
            direction = "NO TRADE"
            confidence = 30
            entry = round(current_price, 2)
            sl = 0
            t1 = t2 = t3 = 0

        # Risk Reward
        if sl and direction != "NO TRADE":
            risk = abs(entry - sl)
            reward = abs(t1 - entry) if t1 else 0
            rr = round(reward / risk, 1) if risk > 0 else 0
        else:
            rr = 0

        return {
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "stop_loss": sl,
            "target_1": t1,
            "target_2": t2,
            "target_3": t3,
            "risk_reward": f"1:{rr}",
            "confidence": confidence,
            "score": round(score, 1),
            "reasons": reasons,
            "timestamp": __import__('datetime').datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:30"),
            "source": "WebSocket" if False else "REST",
        }

    def generate_option_intraday(self, index: str, current_price: float,
                                  pivots: dict, indicators: dict,
                                  volatility: dict = None) -> dict:
        """Generate option-specific intraday signal with CE/PE recommendation."""
        # Normalize pivot keys (support both r1/s1 and resistance_1/support_1)
        norm_pivots = {
            "pivot": pivots.get("pivot", current_price),
            "r1": pivots.get("r1", pivots.get("resistance_1", current_price * 1.005)),
            "r2": pivots.get("r2", pivots.get("resistance_2", current_price * 1.01)),
            "r3": pivots.get("r3", current_price * 1.015),
            "s1": pivots.get("s1", pivots.get("support_1", current_price * 0.995)),
            "s2": pivots.get("s2", pivots.get("support_2", current_price * 0.99)),
            "s3": pivots.get("s3", current_price * 0.985),
        }
        base = self.generate_intraday_signal(index, current_price, norm_pivots, indicators, volatility)

        # Determine option side
        if base["direction"] == "BUY":
            option_side = "CE"
            strike = round(current_price / 50) * 50  # ATM
            option_entry = f"Above {round(current_price + 20, 0)}"
            option_sl = f"Below {round(pivots['pivot'] - 30, 0)}"
            option_target = f"{round(pivots['r1'], 0)} / {round(pivots['r2'], 0)}"
        elif base["direction"] == "SELL":
            option_side = "PE"
            strike = round(current_price / 50) * 50
            option_entry = f"Below {round(current_price - 20, 0)}"
            option_sl = f"Above {round(pivots['pivot'] + 30, 0)}"
            option_target = f"{round(pivots['s1'], 0)} / {round(pivots['s2'], 0)}"
        else:
            option_side = "WAIT"
            strike = round(current_price / 50) * 50
            option_entry = "No clear setup"
            option_sl = "-"
            option_target = "-"

        base["option_side"] = option_side
        base["strike"] = strike
        base["option_entry"] = option_entry
        base["option_sl"] = option_sl
        base["option_target"] = option_target

        return base
