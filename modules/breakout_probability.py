"""
Breakout Probability [Expo] Module
Calculates probability of price breaking above resistance or below support.
Uses ATR, volume, Bollinger squeeze, and price compression analysis.
"""
import pandas as pd
import numpy as np
import ta


class BreakoutProbability:
    """Calculates breakout probability based on multiple factors."""

    def calculate(self, df: pd.DataFrame) -> dict:
        """
        Calculate breakout probability for a stock/index.

        Returns dict with upside/downside breakout probability and signals.
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # 1. Bollinger Band Squeeze (tighter = higher breakout probability)
        bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        bb_width = bb.bollinger_wband()
        current_width = bb_width.iloc[-1]
        avg_width = bb_width.tail(50).mean()
        squeeze_ratio = current_width / avg_width if avg_width > 0 else 1
        squeeze_score = max(0, min(100, int((1 - squeeze_ratio) * 100 + 50)))

        # 2. Volume buildup (increasing volume = breakout imminent)
        vol_sma = volume.rolling(20).mean()
        vol_ratio = volume.iloc[-1] / vol_sma.iloc[-1] if vol_sma.iloc[-1] > 0 else 1
        recent_vol_trend = volume.tail(5).mean() / volume.tail(20).mean() if volume.tail(20).mean() > 0 else 1
        volume_score = min(100, int(recent_vol_trend * 50))

        # 3. Price compression (narrowing range)
        daily_range = (high - low) / close * 100
        recent_range = daily_range.tail(5).mean()
        avg_range = daily_range.tail(20).mean()
        compression = 1 - (recent_range / avg_range) if avg_range > 0 else 0
        compression_score = max(0, min(100, int(compression * 100 + 50)))

        # 4. ADX trend building
        adx = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
        adx_val = adx.adx().iloc[-1]
        adx_rising = adx.adx().iloc[-1] > adx.adx().iloc[-3]
        adx_score = min(100, int(adx_val * 2)) if adx_rising else max(0, int(adx_val))

        # 5. Momentum direction (determines UP vs DOWN breakout)
        rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1]
        macd_ind = ta.trend.MACD(close=close)
        macd_hist = macd_ind.macd_diff().iloc[-1]
        ema_9 = ta.trend.EMAIndicator(close=close, window=9).ema_indicator().iloc[-1]
        ema_21 = ta.trend.EMAIndicator(close=close, window=21).ema_indicator().iloc[-1]

        bullish_factors = 0
        if rsi > 50: bullish_factors += 1
        if macd_hist > 0: bullish_factors += 1
        if ema_9 > ema_21: bullish_factors += 1
        if close.iloc[-1] > close.iloc[-2]: bullish_factors += 1

        # 6. Resistance/Support proximity
        recent_high = high.tail(20).max()
        recent_low = low.tail(20).min()
        current = close.iloc[-1]
        dist_to_resistance = ((recent_high - current) / current) * 100
        dist_to_support = ((current - recent_low) / current) * 100

        near_resistance = dist_to_resistance < 1.5
        near_support = dist_to_support < 1.5

        # Composite breakout probability
        base_probability = (squeeze_score * 0.3 + volume_score * 0.25 +
                           compression_score * 0.25 + adx_score * 0.2)

        # Direction bias
        direction_bias = bullish_factors / 4  # 0 to 1 (1 = fully bullish)

        upside_prob = min(95, int(base_probability * direction_bias * 1.2))
        downside_prob = min(95, int(base_probability * (1 - direction_bias) * 1.2))

        # Breakout signal
        if base_probability > 70 and direction_bias > 0.7:
            signal = "BREAKOUT UP"
            confidence = "High"
        elif base_probability > 70 and direction_bias < 0.3:
            signal = "BREAKDOWN"
            confidence = "High"
        elif base_probability > 55:
            signal = "BREAKOUT BUILDING"
            confidence = "Medium"
        else:
            signal = "NO BREAKOUT"
            confidence = "Low"

        return {
            "breakout_probability": round(base_probability, 1),
            "upside_probability": upside_prob,
            "downside_probability": downside_prob,
            "signal": signal,
            "confidence": confidence,
            "direction_bias": round(direction_bias * 100, 1),
            "factors": {
                "squeeze_score": squeeze_score,
                "volume_score": volume_score,
                "compression_score": compression_score,
                "adx_score": adx_score,
                "vol_ratio": round(vol_ratio, 2),
                "bb_squeeze": round(squeeze_ratio, 3),
                "near_resistance": bool(near_resistance),
                "near_support": bool(near_support),
            },
        }
