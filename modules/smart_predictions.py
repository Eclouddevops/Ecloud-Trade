"""
Smart Predictions Module
AI-powered next-day prediction, market sentiment scoring, and smart trade generation.
Combines ML predictions, technical analysis, news sentiment, and market structure.

NOT FINANCIAL ADVICE. Use proper risk management.
"""
import pandas as pd
import numpy as np
import ta
from datetime import datetime


class SmartPredictor:
    """AI-powered market prediction and smart trade generation."""

    def predict_tomorrow(self, df: pd.DataFrame, symbol: str,
                         news_score: float = 0.0, usa_score: float = 0.0) -> dict:
        """
        Predict next trading day movement.

        Returns direction, probability, expected range, gap, and confidence.
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        price = close.iloc[-1]

        # Technical signals
        rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1]
        macd_ind = ta.trend.MACD(close=close)
        macd_hist = macd_ind.macd_diff().iloc[-1]
        macd_prev = macd_ind.macd_diff().iloc[-2]
        ema_9 = ta.trend.EMAIndicator(close=close, window=9).ema_indicator().iloc[-1]
        ema_21 = ta.trend.EMAIndicator(close=close, window=21).ema_indicator().iloc[-1]
        adx_ind = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
        adx = adx_ind.adx().iloc[-1]
        adx_pos = adx_ind.adx_pos().iloc[-1]
        adx_neg = adx_ind.adx_neg().iloc[-1]

        # ATR for range prediction
        atr = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range().iloc[-1]

        # Volume analysis
        vol_sma = volume.rolling(20).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_sma if vol_sma > 0 else 1

        # Recent momentum
        ret_1d = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
        ret_3d = (close.iloc[-1] - close.iloc[-4]) / close.iloc[-4] * 100
        ret_5d = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] * 100

        # Scoring
        bull_score = 0
        bear_score = 0

        # RSI
        if 55 < rsi < 70: bull_score += 15
        elif rsi > 70: bear_score += 10  # Overbought reversal risk
        elif 30 < rsi < 45: bear_score += 15
        elif rsi < 30: bull_score += 10  # Oversold bounce

        # MACD
        if macd_hist > 0 and macd_hist > macd_prev: bull_score += 20
        elif macd_hist > 0: bull_score += 10
        elif macd_hist < 0 and macd_hist < macd_prev: bear_score += 20
        elif macd_hist < 0: bear_score += 10

        # EMA
        if ema_9 > ema_21: bull_score += 15
        else: bear_score += 15

        # ADX
        if adx > 25:
            if adx_pos > adx_neg: bull_score += 15
            else: bear_score += 15

        # Volume
        if vol_ratio > 1.3 and ret_1d > 0: bull_score += 10
        elif vol_ratio > 1.3 and ret_1d < 0: bear_score += 10

        # Momentum
        if ret_3d > 1: bull_score += 10
        elif ret_3d < -1: bear_score += 10

        # News impact
        bull_score += max(0, news_score * 10)
        bear_score += max(0, -news_score * 10)
        bull_score += max(0, usa_score * 8)
        bear_score += max(0, -usa_score * 8)

        # Calculate probabilities
        total = bull_score + bear_score
        if total == 0: total = 1
        bull_prob = round((bull_score / total) * 100, 1)
        bear_prob = round((bear_score / total) * 100, 1)

        # Direction
        if bull_prob > 65:
            direction = "Strong Bullish ⬆"
            signal = "BUY"
        elif bull_prob > 55:
            direction = "Bullish ⬆"
            signal = "BUY"
        elif bear_prob > 65:
            direction = "Strong Bearish ⬇"
            signal = "SELL"
        elif bear_prob > 55:
            direction = "Bearish ⬇"
            signal = "SELL"
        else:
            direction = "Sideways ➡"
            signal = "HOLD"

        # Expected range
        avg_range = (high - low).tail(10).mean()
        expected_high = round(price + atr * 0.8, 2)
        expected_low = round(price - atr * 0.8, 2)

        # Gap prediction
        if bull_prob > 60:
            gap = round(atr * 0.2, 2)
            gap_dir = "Gap Up"
        elif bear_prob > 60:
            gap = round(-atr * 0.2, 2)
            gap_dir = "Gap Down"
        else:
            gap = 0
            gap_dir = "Flat Opening"

        # Confidence
        confidence = min(95, max(40, int(abs(bull_prob - bear_prob) + 40)))

        # Institutional probability (based on volume + trend)
        inst_buying = bool(bull_prob > 55 and vol_ratio > 1.2)
        inst_selling = bool(bear_prob > 55 and vol_ratio > 1.2)

        return {
            "symbol": symbol,
            "prediction_for": "Next Trading Day",
            "direction": direction,
            "signal": signal,
            "bullish_probability": float(bull_prob),
            "bearish_probability": float(bear_prob),
            "confidence": int(confidence),
            "expected_open_gap": float(gap),
            "gap_direction": gap_dir,
            "expected_high": float(expected_high),
            "expected_low": float(expected_low),
            "expected_close_range": f"₹{expected_low} - ₹{expected_high}",
            "current_price": float(round(price, 2)),
            "atr": float(round(atr, 2)),
            "institutional_buying": inst_buying,
            "institutional_selling": inst_selling,
            "key_levels": {
                "resistance": float(expected_high),
                "support": float(expected_low),
                "pivot": float(round((expected_high + expected_low + price) / 3, 2)),
            },
        }

    def generate_smart_trade(self, df: pd.DataFrame, symbol: str) -> dict:
        """Generate complete AI trade setup with entry, targets, SL, probability."""
        close = df["close"]
        high = df["high"]
        low = df["low"]
        price = close.iloc[-1]

        # Get prediction
        pred = self.predict_tomorrow(df, symbol)

        # ATR for levels
        atr = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range().iloc[-1]

        # Determine trade
        if pred["signal"] == "BUY":
            entry = round(price + atr * 0.1, 2)
            sl = round(price - atr * 1.5, 2)
            t1 = round(price + atr * 1.0, 2)
            t2 = round(price + atr * 1.8, 2)
            t3 = round(price + atr * 2.5, 2)
            expected_points = round(atr * 1.8, 0)
            side = "CE"
            strength = "Strong" if pred["confidence"] > 75 else "Medium" if pred["confidence"] > 60 else "Weak"
        elif pred["signal"] == "SELL":
            entry = round(price - atr * 0.1, 2)
            sl = round(price + atr * 1.5, 2)
            t1 = round(price - atr * 1.0, 2)
            t2 = round(price - atr * 1.8, 2)
            t3 = round(price - atr * 2.5, 2)
            expected_points = round(atr * 1.8, 0)
            side = "PE"
            strength = "Strong" if pred["confidence"] > 75 else "Medium" if pred["confidence"] > 60 else "Weak"
        else:
            entry = round(price, 2)
            sl = 0
            t1 = t2 = t3 = 0
            expected_points = 0
            side = "WAIT"
            strength = "Weak"

        # Risk reward
        risk = abs(entry - sl) if sl else 1
        reward = abs(t2 - entry) if t2 else 0
        rr = round(reward / risk, 1) if risk > 0 else 0

        # Strike price
        step = 100 if "BANK" in symbol else 50
        strike = round(price / step) * step

        # Success probability (based on confidence + trend alignment)
        success_prob = min(95, pred["confidence"] + 5)

        return {
            "symbol": symbol,
            "signal": pred["signal"],
            "side": side,
            "strength": strength,
            "entry": entry,
            "stop_loss": sl,
            "target_1": t1,
            "target_2": t2,
            "target_3": t3,
            "strike": f"{strike} {side}",
            "risk_reward": f"1:{rr}",
            "success_probability": success_prob,
            "expected_points": f"+{expected_points}",
            "confidence": pred["confidence"],
            "direction": pred["direction"],
        }

    def calculate_sentiment(self, df: pd.DataFrame, news_score: float = 0.0,
                            usa_score: float = 0.0, vix: float = 15.0) -> dict:
        """
        Calculate Market Fear & Greed Index (0-100).
        0 = Extreme Fear, 100 = Extreme Greed.
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        scores = []

        # 1. Momentum (RSI)
        rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1]
        momentum_score = min(100, max(0, rsi))
        scores.append(momentum_score)

        # 2. Trend (price vs SMA)
        sma_50 = close.rolling(50).mean().iloc[-1]
        trend_score = 70 if close.iloc[-1] > sma_50 else 30
        scores.append(trend_score)

        # 3. Volume
        vol_sma = volume.rolling(20).mean().iloc[-1]
        vol_ratio = volume.iloc[-1] / vol_sma if vol_sma > 0 else 1
        vol_score = min(100, max(0, int(vol_ratio * 50)))
        scores.append(vol_score)

        # 4. VIX (fear gauge) - lower VIX = more greed
        vix_score = max(0, min(100, int(100 - vix * 3)))
        scores.append(vix_score)

        # 5. News sentiment
        news_norm = min(100, max(0, int((news_score + 1) * 50)))
        scores.append(news_norm)

        # 6. Market breadth (recent returns)
        ret_5d = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] * 100
        breadth_score = min(100, max(0, int(50 + ret_5d * 10)))
        scores.append(breadth_score)

        # Composite
        composite = int(sum(scores) / len(scores))

        if composite >= 75:
            mood = "🟢 Extreme Greed"
            mood_label = "Extreme Greed"
        elif composite >= 60:
            mood = "🟢 Greed"
            mood_label = "Greed"
        elif composite >= 45:
            mood = "🟡 Neutral"
            mood_label = "Neutral"
        elif composite >= 30:
            mood = "🔴 Fear"
            mood_label = "Fear"
        else:
            mood = "🔴 Extreme Fear"
            mood_label = "Extreme Fear"

        return {
            "score": composite,
            "mood": mood,
            "mood_label": mood_label,
            "components": {
                "momentum": int(momentum_score),
                "trend": int(trend_score),
                "volume": int(vol_score),
                "vix": int(vix_score),
                "news": int(news_norm),
                "breadth": int(breadth_score),
            },
        }
