"""
GainzAlgo V2 Alpha Indicator
Combines momentum, trend-following, volatility analysis, and multi-timeframe
confluence to generate high-probability BUY/SELL signals with entry/exit levels.

Inspired by the GainzAlgo concept of layered algorithmic logic that adapts
to varying market conditions.

NOT FINANCIAL ADVICE. Use proper risk management.
"""
import pandas as pd
import numpy as np
import ta


class GainzAlgoV2Alpha:
    """
    GainzAlgo V2 Alpha — Advanced multi-layer trading signal generator.

    Combines:
    - Momentum analysis (RSI, MACD, Stochastic)
    - Trend detection (EMA crossovers, ADX, Supertrend)
    - Volatility normalization (ATR, Bollinger squeeze)
    - Volume confirmation (OBV, volume spikes)
    - Price action (candle structure, support/resistance)
    - Multi-timeframe confluence scoring
    """

    def __init__(self):
        self.signal_history = []

    def analyze(self, df: pd.DataFrame, symbol: str = "") -> dict:
        """
        Run full GainzAlgo V2 Alpha analysis on OHLCV data.

        Args:
            df: DataFrame with columns [open, high, low, close, volume]
            symbol: Symbol name for display

        Returns:
            Complete analysis with signal, entry, exit, confidence
        """
        if len(df) < 50:
            return {"error": "Insufficient data (need 50+ candles)", "symbol": symbol}

        df = df.copy()

        # Layer 1: Trend Detection
        trend_score, trend_data = self._layer_trend(df)

        # Layer 2: Momentum Analysis
        momentum_score, momentum_data = self._layer_momentum(df)

        # Layer 3: Volatility & Squeeze Detection
        volatility_score, volatility_data = self._layer_volatility(df)

        # Layer 4: Volume Confirmation
        volume_score, volume_data = self._layer_volume(df)

        # Layer 5: Price Action & Structure
        structure_score, structure_data = self._layer_structure(df)

        # Layer 6: Multi-Timeframe Confluence
        mtf_score = self._layer_mtf_confluence(df)

        # Composite Signal Generation
        total_score = (
            trend_score * 0.25 +
            momentum_score * 0.20 +
            volatility_score * 0.15 +
            volume_score * 0.15 +
            structure_score * 0.15 +
            mtf_score * 0.10
        )

        # Generate signal
        signal = self._generate_signal(total_score, df, trend_data, volatility_data)

        return {
            "symbol": symbol,
            "signal": signal["action"],
            "side": signal["side"],
            "confidence": signal["confidence"],
            "entry_price": signal["entry"],
            "stop_loss": signal["stop_loss"],
            "target_1": signal["target_1"],
            "target_2": signal["target_2"],
            "target_3": signal["target_3"],
            "exit_price": signal["exit"],
            "expected_points": signal["expected_points"],
            "risk_reward": signal["risk_reward"],
            "current_price": round(df["close"].iloc[-1], 2),
            "composite_score": round(total_score, 2),
            "layer_scores": {
                "trend": round(trend_score, 2),
                "momentum": round(momentum_score, 2),
                "volatility": round(volatility_score, 2),
                "volume": round(volume_score, 2),
                "structure": round(structure_score, 2),
                "mtf_confluence": round(mtf_score, 2),
            },
            "trend_data": trend_data,
            "momentum_data": momentum_data,
            "volatility_data": volatility_data,
            "reasons": signal["reasons"],
        }

    def _layer_trend(self, df: pd.DataFrame) -> tuple:
        """Layer 1: Trend Detection using EMA crossovers, ADX, Supertrend."""
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # EMA crossovers
        ema_9 = ta.trend.EMAIndicator(close=close, window=9).ema_indicator()
        ema_21 = ta.trend.EMAIndicator(close=close, window=21).ema_indicator()
        ema_50 = ta.trend.EMAIndicator(close=close, window=50).ema_indicator()

        ema_9_val = ema_9.iloc[-1]
        ema_21_val = ema_21.iloc[-1]
        ema_50_val = ema_50.iloc[-1]
        price = close.iloc[-1]

        # ADX for trend strength
        adx_ind = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
        adx = adx_ind.adx().iloc[-1]
        adx_pos = adx_ind.adx_pos().iloc[-1]
        adx_neg = adx_ind.adx_neg().iloc[-1]

        # Supertrend approximation (ATR-based)
        atr = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=10).average_true_range()
        supertrend_upper = (high + low) / 2 + 2 * atr
        supertrend_lower = (high + low) / 2 - 2 * atr
        above_supertrend = price > supertrend_lower.iloc[-1]

        # Score calculation (-100 to +100)
        score = 0
        if ema_9_val > ema_21_val > ema_50_val:
            score += 40  # Strong bullish alignment
        elif ema_9_val > ema_21_val:
            score += 20
        elif ema_9_val < ema_21_val < ema_50_val:
            score -= 40  # Strong bearish alignment
        elif ema_9_val < ema_21_val:
            score -= 20

        if price > ema_9_val:
            score += 15
        else:
            score -= 15

        if adx > 25:
            if adx_pos > adx_neg:
                score += 25
            else:
                score -= 25
        elif adx > 20:
            if adx_pos > adx_neg:
                score += 10
            else:
                score -= 10

        if above_supertrend:
            score += 20
        else:
            score -= 20

        trend = "Bullish" if score > 20 else "Bearish" if score < -20 else "Sideways"

        data = {
            "trend": trend,
            "ema_9": round(float(ema_9_val), 2),
            "ema_21": round(float(ema_21_val), 2),
            "ema_50": round(float(ema_50_val), 2),
            "adx": round(float(adx), 2),
            "supertrend": "Above" if above_supertrend else "Below",
        }

        return score, data

    def _layer_momentum(self, df: pd.DataFrame) -> tuple:
        """Layer 2: Momentum Analysis using RSI, MACD, Stochastic."""
        close = df["close"]

        # RSI
        rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi()
        rsi_val = rsi.iloc[-1]
        rsi_prev = rsi.iloc[-2]

        # MACD
        macd_ind = ta.trend.MACD(close=close, window_fast=12, window_slow=26, window_sign=9)
        macd = macd_ind.macd().iloc[-1]
        macd_signal = macd_ind.macd_signal().iloc[-1]
        macd_hist = macd_ind.macd_diff().iloc[-1]
        macd_hist_prev = macd_ind.macd_diff().iloc[-2]

        # Stochastic
        stoch = ta.momentum.StochasticOscillator(high=df["high"], low=df["low"], close=close)
        stoch_k = stoch.stoch().iloc[-1]
        stoch_d = stoch.stoch_signal().iloc[-1]

        score = 0

        # RSI scoring
        if 55 < rsi_val < 70:
            score += 25  # Bullish momentum
        elif rsi_val > 70:
            score += 10  # Overbought but still up
        elif 30 < rsi_val < 45:
            score -= 25  # Bearish momentum
        elif rsi_val < 30:
            score -= 10  # Oversold bounce possible

        # RSI direction
        if rsi_val > rsi_prev:
            score += 10
        else:
            score -= 10

        # MACD
        if macd > macd_signal and macd_hist > 0:
            score += 30
        elif macd > macd_signal:
            score += 15
        elif macd < macd_signal and macd_hist < 0:
            score -= 30
        elif macd < macd_signal:
            score -= 15

        # MACD histogram acceleration
        if macd_hist > macd_hist_prev and macd_hist > 0:
            score += 10  # Accelerating bullish
        elif macd_hist < macd_hist_prev and macd_hist < 0:
            score -= 10  # Accelerating bearish

        # Stochastic
        if stoch_k > stoch_d and stoch_k < 80:
            score += 15
        elif stoch_k < stoch_d and stoch_k > 20:
            score -= 15

        data = {
            "rsi": round(float(rsi_val), 2),
            "rsi_direction": "Rising" if rsi_val > rsi_prev else "Falling",
            "macd_crossover": "Bullish" if macd > macd_signal else "Bearish",
            "macd_histogram": round(float(macd_hist), 4),
            "stochastic_k": round(float(stoch_k), 2),
            "momentum": "Strong Bullish" if score > 40 else "Bullish" if score > 15 else "Strong Bearish" if score < -40 else "Bearish" if score < -15 else "Neutral",
        }

        return score, data

    def _layer_volatility(self, df: pd.DataFrame) -> tuple:
        """Layer 3: Volatility & Squeeze Detection."""
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # ATR
        atr = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
        atr_val = atr.iloc[-1]
        atr_pct = (atr_val / close.iloc[-1]) * 100

        # Bollinger Bands squeeze
        bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        bb_width = bb.bollinger_wband()
        current_width = bb_width.iloc[-1]
        avg_width = bb_width.tail(50).mean()
        squeeze_ratio = current_width / avg_width if avg_width > 0 else 1

        # Keltner Channel approximation for squeeze detection
        is_squeeze = squeeze_ratio < 0.7  # Tight squeeze

        # Price position in Bollinger
        bb_upper = bb.bollinger_hband().iloc[-1]
        bb_lower = bb.bollinger_lband().iloc[-1]
        bb_mid = bb.bollinger_mavg().iloc[-1]
        price = close.iloc[-1]
        bb_position = (price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5

        score = 0
        # Squeeze = potential breakout
        if is_squeeze:
            score += 20  # Breakout imminent

        # Position in bands
        if bb_position > 0.8:
            score += 15  # Near upper band (bullish momentum)
        elif bb_position < 0.2:
            score -= 15  # Near lower band (bearish)
        elif 0.5 < bb_position < 0.7:
            score += 5

        # Volatility expansion
        if current_width > avg_width * 1.2:
            score += 10  # Expanding volatility (trend move)

        data = {
            "atr": round(float(atr_val), 2),
            "atr_pct": round(float(atr_pct), 2),
            "squeeze": bool(is_squeeze),
            "squeeze_ratio": round(float(squeeze_ratio), 3),
            "bb_position": round(float(bb_position * 100), 1),
            "expected_move": round(float(atr_val * 1.5), 2),
        }

        return score, data

    def _layer_volume(self, df: pd.DataFrame) -> tuple:
        """Layer 4: Volume Confirmation."""
        volume = df["volume"]
        close = df["close"]

        # Volume moving average
        vol_sma = volume.rolling(20).mean()
        vol_ratio = volume.iloc[-1] / vol_sma.iloc[-1] if vol_sma.iloc[-1] > 0 else 1

        # OBV trend
        obv = ta.volume.OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
        obv_sma = obv.rolling(10).mean()
        obv_rising = obv.iloc[-1] > obv_sma.iloc[-1]

        # Volume spike detection
        vol_spike = vol_ratio > 1.5

        # Price-volume agreement
        price_up = close.iloc[-1] > close.iloc[-2]
        vol_up = volume.iloc[-1] > volume.iloc[-2]
        agreement = (price_up and vol_up) or (not price_up and vol_up)

        score = 0
        if vol_spike and price_up:
            score += 30  # Bullish volume spike
        elif vol_spike and not price_up:
            score -= 30  # Bearish volume spike
        elif vol_ratio > 1.2 and price_up:
            score += 15
        elif vol_ratio > 1.2 and not price_up:
            score -= 15

        if obv_rising:
            score += 20
        else:
            score -= 20

        if agreement:
            score += 10

        data = {
            "volume_ratio": round(float(vol_ratio), 2),
            "obv_trend": "Rising" if obv_rising else "Falling",
            "volume_spike": bool(vol_spike),
            "confirmation": "Confirmed" if agreement else "Divergence",
        }

        return score, data

    def _layer_structure(self, df: pd.DataFrame) -> tuple:
        """Layer 5: Price Action & Market Structure."""
        close = df["close"]
        high = df["high"]
        low = df["low"]
        open_p = df["open"]

        # Higher highs / lower lows
        recent_highs = high.tail(10)
        recent_lows = low.tail(10)
        hh = recent_highs.iloc[-1] > recent_highs.iloc[-5]  # Higher high
        hl = recent_lows.iloc[-1] > recent_lows.iloc[-5]  # Higher low
        lh = recent_highs.iloc[-1] < recent_highs.iloc[-5]  # Lower high
        ll = recent_lows.iloc[-1] < recent_lows.iloc[-5]  # Lower low

        # Candle strength
        body = abs(close.iloc[-1] - open_p.iloc[-1])
        total_range = high.iloc[-1] - low.iloc[-1]
        body_ratio = body / total_range if total_range > 0 else 0
        is_bullish_candle = close.iloc[-1] > open_p.iloc[-1]

        # Support/Resistance proximity
        pivot = (high.iloc[-2] + low.iloc[-2] + close.iloc[-2]) / 3
        r1 = 2 * pivot - low.iloc[-2]
        s1 = 2 * pivot - high.iloc[-2]
        price = close.iloc[-1]
        near_support = abs(price - s1) / price < 0.005
        near_resistance = abs(price - r1) / price < 0.005

        score = 0
        if hh and hl:
            score += 30  # Bullish structure
        elif lh and ll:
            score -= 30  # Bearish structure

        if is_bullish_candle and body_ratio > 0.7:
            score += 20  # Strong bullish candle
        elif not is_bullish_candle and body_ratio > 0.7:
            score -= 20  # Strong bearish candle

        if near_support and is_bullish_candle:
            score += 15  # Bounce from support
        elif near_resistance and not is_bullish_candle:
            score -= 15  # Rejection at resistance

        structure = "Bullish" if (hh and hl) else "Bearish" if (lh and ll) else "Ranging"

        data = {
            "structure": structure,
            "higher_high": bool(hh),
            "higher_low": bool(hl),
            "candle_strength": round(float(body_ratio * 100), 1),
            "last_candle": "Bullish" if is_bullish_candle else "Bearish",
            "pivot": round(float(pivot), 2),
            "r1": round(float(r1), 2),
            "s1": round(float(s1), 2),
        }

        return score, data

    def _layer_mtf_confluence(self, df: pd.DataFrame) -> tuple:
        """Layer 6: Multi-Timeframe Confluence (simulated with different lookbacks)."""
        close = df["close"]

        # Short-term (5-period)
        short_trend = 1 if close.iloc[-1] > close.iloc[-5] else -1

        # Medium-term (20-period)
        med_trend = 1 if close.iloc[-1] > close.iloc[-20] else -1

        # Long-term (50-period)
        long_trend = 1 if close.iloc[-1] > close.iloc[min(-50, -len(close)+1)] else -1

        # Confluence: all aligned = strong signal
        alignment = short_trend + med_trend + long_trend

        if alignment == 3:
            score = 80  # All bullish
        elif alignment == -3:
            score = -80  # All bearish
        elif alignment >= 2:
            score = 40
        elif alignment <= -2:
            score = -40
        else:
            score = 0

        return score

    def _generate_signal(self, total_score: float, df: pd.DataFrame,
                         trend_data: dict, volatility_data: dict) -> dict:
        """Generate final trading signal with entry, SL, targets."""
        price = df["close"].iloc[-1]
        atr = volatility_data["atr"]
        expected_move = volatility_data["expected_move"]

        reasons = []

        # Determine action
        if total_score >= 50:
            action = "STRONG BUY"
            side = "CE"
            confidence = min(95, 70 + int((total_score - 50) * 0.5))
            reasons.append(f"Strong bullish confluence (score: {total_score:.0f})")
        elif total_score >= 25:
            action = "BUY"
            side = "CE"
            confidence = min(85, 55 + int((total_score - 25) * 0.6))
            reasons.append(f"Bullish bias confirmed (score: {total_score:.0f})")
        elif total_score <= -50:
            action = "STRONG SELL"
            side = "PE"
            confidence = min(95, 70 + int((abs(total_score) - 50) * 0.5))
            reasons.append(f"Strong bearish confluence (score: {total_score:.0f})")
        elif total_score <= -25:
            action = "SELL"
            side = "PE"
            confidence = min(85, 55 + int((abs(total_score) - 25) * 0.6))
            reasons.append(f"Bearish bias confirmed (score: {total_score:.0f})")
        else:
            action = "WAIT"
            side = "NEUTRAL"
            confidence = 30
            reasons.append(f"No clear signal (score: {total_score:.0f})")

        # Add layer reasons
        if trend_data["trend"] == "Bullish":
            reasons.append(f"Trend: Bullish (EMA aligned, ADX {trend_data['adx']})")
        elif trend_data["trend"] == "Bearish":
            reasons.append(f"Trend: Bearish (EMA bearish, ADX {trend_data['adx']})")

        if volatility_data["squeeze"]:
            reasons.append("Bollinger squeeze detected — breakout imminent")

        # Calculate levels
        if side == "CE":
            entry = round(price + atr * 0.2, 2)
            stop_loss = round(price - atr * 1.5, 2)
            target_1 = round(price + expected_move * 0.7, 2)
            target_2 = round(price + expected_move, 2)
            target_3 = round(price + expected_move * 1.5, 2)
            exit_price = target_2
            expected_points = round(expected_move, 0)
        elif side == "PE":
            entry = round(price - atr * 0.2, 2)
            stop_loss = round(price + atr * 1.5, 2)
            target_1 = round(price - expected_move * 0.7, 2)
            target_2 = round(price - expected_move, 2)
            target_3 = round(price - expected_move * 1.5, 2)
            exit_price = target_2
            expected_points = round(expected_move, 0)
        else:
            entry = round(price, 2)
            stop_loss = 0
            target_1 = target_2 = target_3 = 0
            exit_price = 0
            expected_points = 0

        # Risk:Reward
        risk = abs(entry - stop_loss) if stop_loss else 1
        reward = abs(target_2 - entry) if target_2 else 0
        rr = round(reward / risk, 1) if risk > 0 else 0

        return {
            "action": action,
            "side": side,
            "confidence": confidence,
            "entry": entry,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "target_3": target_3,
            "exit": exit_price,
            "expected_points": expected_points,
            "risk_reward": f"1:{rr}",
            "reasons": reasons,
        }
