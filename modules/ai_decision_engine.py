"""
AI Decision Engine — Unified Trade Recommendation
Resolves conflicting indicator signals using priority-based logic.
Combines multi-timeframe analysis, price action, volume, momentum,
and market structure into a single actionable verdict.

Priority Order (when indicators conflict):
1. Higher Timeframe Trend
2. Price Action & Market Structure
3. Volume Confirmation
4. Open Interest / Momentum Direction
5. Momentum Indicators (RSI/MACD)
6. Lagging Indicators (EMA/SMA)

NOT FINANCIAL ADVICE. Use proper risk management.
"""
import pandas as pd
import numpy as np
import ta
from datetime import datetime


class AIDecisionEngine:
    """Unified AI decision engine that resolves conflicting signals."""

    def deep_analysis(self, df: pd.DataFrame, symbol: str) -> dict:
        """
        Perform comprehensive multi-layer analysis and resolve conflicts.

        Args:
            df: DataFrame with OHLCV data (ideally 6mo+ daily)
            symbol: Symbol name

        Returns:
            Complete analysis with unified verdict
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        open_p = df["open"]
        price = float(close.iloc[-1])

        # ─── Multi-Timeframe Trend ──────────────────────────────────────
        tf_analysis = self._multi_timeframe_trend(df)

        # ─── Price Action & Structure ───────────────────────────────────
        structure = self._price_action_structure(df)

        # ─── Volume Analysis ────────────────────────────────────────────
        vol_analysis = self._volume_analysis(df)

        # ─── Momentum ───────────────────────────────────────────────────
        momentum = self._momentum_analysis(df)

        # ─── Trend Indicators ───────────────────────────────────────────
        trend_ind = self._trend_indicators(df)

        # ─── Volatility ─────────────────────────────────────────────────
        volatility = self._volatility_analysis(df)

        # ─── Key Levels ─────────────────────────────────────────────────
        levels = self._key_levels(df)

        # ─── Conflict Resolution ────────────────────────────────────────
        verdict = self._resolve_conflicts(
            tf_analysis, structure, vol_analysis, momentum, trend_ind, volatility, price
        )

        # ─── Trade Setup ────────────────────────────────────────────────
        trade = self._generate_trade(verdict, levels, volatility, price, symbol)

        return {
            "symbol": symbol,
            "current_price": price,
            "timestamp": datetime.now().isoformat(),
            "verdict": verdict,
            "trade_setup": trade,
            "analysis": {
                "timeframe_trend": tf_analysis,
                "price_action": structure,
                "volume": vol_analysis,
                "momentum": momentum,
                "trend_indicators": trend_ind,
                "volatility": volatility,
            },
            "key_levels": levels,
            "conflict_resolution": verdict["conflict_log"],
        }

    def _multi_timeframe_trend(self, df: pd.DataFrame) -> dict:
        """Analyze trend across multiple simulated timeframes."""
        close = df["close"]

        # Daily (last 5 candles)
        daily_trend = "Bullish" if close.iloc[-1] > close.iloc[-2] > close.iloc[-3] else \
                      "Bearish" if close.iloc[-1] < close.iloc[-2] < close.iloc[-3] else "Sideways"

        # Weekly (last 5 days vs 5 before)
        weekly_avg_recent = close.tail(5).mean()
        weekly_avg_prev = close.iloc[-10:-5].mean()
        weekly_trend = "Bullish" if weekly_avg_recent > weekly_avg_prev else "Bearish"

        # Monthly (last 20 days vs 20 before)
        monthly_recent = close.tail(20).mean()
        monthly_prev = close.iloc[-40:-20].mean() if len(close) > 40 else close.iloc[:20].mean()
        monthly_trend = "Bullish" if monthly_recent > monthly_prev else "Bearish"

        # SMA alignment
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1]
        sma_200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else close.rolling(min(len(close), 100)).mean().iloc[-1]

        if close.iloc[-1] > sma_20 > sma_50:
            higher_tf = "Bullish"
            score = 80
        elif close.iloc[-1] < sma_20 < sma_50:
            higher_tf = "Bearish"
            score = -80
        elif close.iloc[-1] > sma_50:
            higher_tf = "Mildly Bullish"
            score = 30
        elif close.iloc[-1] < sma_50:
            higher_tf = "Mildly Bearish"
            score = -30
        else:
            higher_tf = "Neutral"
            score = 0

        return {
            "dominant_trend": higher_tf,
            "score": int(score),
            "daily": daily_trend,
            "weekly": weekly_trend,
            "monthly": monthly_trend,
            "price_vs_sma20": "Above" if close.iloc[-1] > sma_20 else "Below",
            "price_vs_sma50": "Above" if close.iloc[-1] > sma_50 else "Below",
        }

    def _price_action_structure(self, df: pd.DataFrame) -> dict:
        """Analyze price action and market structure."""
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # Higher Highs / Lower Lows (last 20 candles)
        recent = df.tail(20)
        highs_5 = high.tail(5).max()
        highs_10 = high.iloc[-10:-5].max()
        lows_5 = low.tail(5).min()
        lows_10 = low.iloc[-10:-5].min()

        hh = float(highs_5) > float(highs_10)
        hl = float(lows_5) > float(lows_10)
        lh = float(highs_5) < float(highs_10)
        ll = float(lows_5) < float(lows_10)

        if hh and hl:
            structure = "Bullish (HH + HL)"
            score = 70
        elif lh and ll:
            structure = "Bearish (LH + LL)"
            score = -70
        elif hh and ll:
            structure = "Expanding (Volatile)"
            score = 0
        else:
            structure = "Ranging"
            score = 0

        # Candle strength
        body = abs(close.iloc[-1] - df["open"].iloc[-1])
        total_range = high.iloc[-1] - low.iloc[-1]
        body_pct = (body / total_range * 100) if total_range > 0 else 50
        is_bullish = close.iloc[-1] > df["open"].iloc[-1]

        return {
            "structure": structure,
            "score": int(score),
            "higher_high": bool(hh),
            "higher_low": bool(hl),
            "lower_high": bool(lh),
            "lower_low": bool(ll),
            "last_candle": "Strong Bullish" if is_bullish and body_pct > 70 else "Strong Bearish" if not is_bullish and body_pct > 70 else "Bullish" if is_bullish else "Bearish",
            "body_strength": float(round(body_pct, 1)),
        }

    def _volume_analysis(self, df: pd.DataFrame) -> dict:
        """Volume confirmation analysis."""
        volume = df["volume"]
        close = df["close"]

        vol_sma = volume.rolling(20).mean().iloc[-1]
        vol_ratio = float(volume.iloc[-1] / vol_sma) if vol_sma > 0 else 1.0
        vol_increasing = float(volume.tail(3).mean()) > float(volume.tail(10).mean())

        # Price-volume agreement
        price_up = close.iloc[-1] > close.iloc[-2]
        vol_up = volume.iloc[-1] > vol_sma

        if price_up and vol_up:
            confirmation = "Bullish (price up + volume up)"
            score = 60
        elif not price_up and vol_up:
            confirmation = "Bearish (price down + volume up)"
            score = -60
        elif price_up and not vol_up:
            confirmation = "Weak Bullish (price up, low volume)"
            score = 20
        else:
            confirmation = "Weak Bearish (price down, low volume)"
            score = -20

        return {
            "confirmation": confirmation,
            "score": int(score),
            "volume_ratio": float(round(vol_ratio, 2)),
            "volume_increasing": bool(vol_increasing),
            "volume_spike": bool(vol_ratio > 1.5),
        }

    def _momentum_analysis(self, df: pd.DataFrame) -> dict:
        """RSI, MACD, Stochastic momentum analysis."""
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # RSI
        rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1]

        # MACD
        macd_ind = ta.trend.MACD(close=close)
        macd_hist = macd_ind.macd_diff().iloc[-1]
        macd_prev = macd_ind.macd_diff().iloc[-2]
        macd_rising = macd_hist > macd_prev

        # Stochastic
        stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close)
        stoch_k = stoch.stoch().iloc[-1]

        # Score
        score = 0
        if rsi > 60: score += 25
        elif rsi < 40: score -= 25

        if macd_hist > 0 and macd_rising: score += 35
        elif macd_hist > 0: score += 15
        elif macd_hist < 0 and not macd_rising: score -= 35
        elif macd_hist < 0: score -= 15

        if stoch_k > 60: score += 15
        elif stoch_k < 40: score -= 15

        direction = "Bullish" if score > 20 else "Bearish" if score < -20 else "Neutral"

        return {
            "direction": direction,
            "score": int(score),
            "rsi": float(round(rsi, 2)),
            "rsi_signal": "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral",
            "macd": "Bullish" if macd_hist > 0 else "Bearish",
            "macd_rising": bool(macd_rising),
            "stochastic": float(round(stoch_k, 2)),
        }

    def _trend_indicators(self, df: pd.DataFrame) -> dict:
        """EMA, ADX, VWAP, Supertrend analysis."""
        close = df["close"]
        high = df["high"]
        low = df["low"]

        ema_9 = ta.trend.EMAIndicator(close=close, window=9).ema_indicator().iloc[-1]
        ema_21 = ta.trend.EMAIndicator(close=close, window=21).ema_indicator().iloc[-1]
        ema_50 = ta.trend.EMAIndicator(close=close, window=50).ema_indicator().iloc[-1]

        adx_ind = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
        adx = adx_ind.adx().iloc[-1]
        adx_pos = adx_ind.adx_pos().iloc[-1]
        adx_neg = adx_ind.adx_neg().iloc[-1]

        # VWAP approximation
        tp = (high + low + close) / 3
        vwap = float((tp * df["volume"]).rolling(20).sum().iloc[-1] / df["volume"].rolling(20).sum().iloc[-1])

        price = float(close.iloc[-1])
        score = 0
        if ema_9 > ema_21: score += 25
        else: score -= 25
        if price > vwap: score += 20
        else: score -= 20
        if adx > 25 and adx_pos > adx_neg: score += 30
        elif adx > 25 and adx_neg > adx_pos: score -= 30

        return {
            "score": int(score),
            "ema_trend": "Bullish" if ema_9 > ema_21 else "Bearish",
            "ema_9": float(round(ema_9, 2)),
            "ema_21": float(round(ema_21, 2)),
            "ema_50": float(round(ema_50, 2)),
            "vwap": float(round(vwap, 2)),
            "price_vs_vwap": "Above" if price > vwap else "Below",
            "adx": float(round(adx, 2)),
            "adx_trend": "Strong" if adx > 25 else "Weak",
            "adx_direction": "Bullish" if adx_pos > adx_neg else "Bearish",
        }

    def _volatility_analysis(self, df: pd.DataFrame) -> dict:
        """ATR and Bollinger analysis for position sizing."""
        close = df["close"]
        high = df["high"]
        low = df["low"]

        atr = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range().iloc[-1]
        bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        bb_upper = bb.bollinger_hband().iloc[-1]
        bb_lower = bb.bollinger_lband().iloc[-1]
        bb_width = bb.bollinger_wband().iloc[-1]
        avg_width = bb.bollinger_wband().tail(50).mean()
        squeeze = bb_width < avg_width * 0.7

        return {
            "atr": float(round(atr, 2)),
            "expected_move": float(round(atr * 1.5, 2)),
            "bb_upper": float(round(bb_upper, 2)),
            "bb_lower": float(round(bb_lower, 2)),
            "squeeze": bool(squeeze),
            "volatility": "High" if atr / float(close.iloc[-1]) > 0.02 else "Normal" if atr / float(close.iloc[-1]) > 0.01 else "Low",
        }

    def _key_levels(self, df: pd.DataFrame) -> dict:
        """Calculate support, resistance, breakout/breakdown levels."""
        high = df["high"]
        low = df["low"]
        close = df["close"]
        price = float(close.iloc[-1])

        # Pivot
        prev_h = float(high.iloc[-2])
        prev_l = float(low.iloc[-2])
        prev_c = float(close.iloc[-2])
        pivot = (prev_h + prev_l + prev_c) / 3
        r1 = 2 * pivot - prev_l
        r2 = pivot + (prev_h - prev_l)
        s1 = 2 * pivot - prev_h
        s2 = pivot - (prev_h - prev_l)

        # Recent swing high/low
        swing_high = float(high.tail(20).max())
        swing_low = float(low.tail(20).min())

        # Breakout/breakdown levels
        breakout = float(high.tail(10).max())
        breakdown = float(low.tail(10).min())

        return {
            "pivot": round(pivot, 2),
            "resistance_1": round(r1, 2),
            "resistance_2": round(r2, 2),
            "support_1": round(s1, 2),
            "support_2": round(s2, 2),
            "swing_high": round(swing_high, 2),
            "swing_low": round(swing_low, 2),
            "breakout_level": round(breakout, 2),
            "breakdown_level": round(breakdown, 2),
        }

    def _resolve_conflicts(self, tf, structure, volume, momentum, trend, volatility, price) -> dict:
        """
        Resolve conflicting signals using priority hierarchy.
        Priority: Higher TF > Price Action > Volume > Momentum > Trend Indicators
        """
        conflict_log = []
        scores = []

        # Priority 1: Higher Timeframe (weight 3x)
        scores.append(("Timeframe", tf["score"], 3))
        conflict_log.append(f"P1 Higher TF: {tf['dominant_trend']} (score: {tf['score']})")

        # Priority 2: Price Action (weight 2.5x)
        scores.append(("Structure", structure["score"], 2.5))
        conflict_log.append(f"P2 Structure: {structure['structure']} (score: {structure['score']})")

        # Priority 3: Volume (weight 2x)
        scores.append(("Volume", volume["score"], 2))
        conflict_log.append(f"P3 Volume: {volume['confirmation']} (score: {volume['score']})")

        # Priority 4: Momentum (weight 1.5x)
        scores.append(("Momentum", momentum["score"], 1.5))
        conflict_log.append(f"P4 Momentum: {momentum['direction']} RSI={momentum['rsi']} (score: {momentum['score']})")

        # Priority 5: Trend Indicators (weight 1x)
        scores.append(("Trend Ind", trend["score"], 1))
        conflict_log.append(f"P5 Trend Ind: EMA={trend['ema_trend']} VWAP={trend['price_vs_vwap']} (score: {trend['score']})")

        # Weighted composite
        total_weight = sum(w for _, _, w in scores)
        weighted_score = sum(s * w for _, s, w in scores) / total_weight

        # Detect conflicts
        bullish_count = sum(1 for _, s, _ in scores if s > 15)
        bearish_count = sum(1 for _, s, _ in scores if s < -15)
        has_conflict = bullish_count > 0 and bearish_count > 0

        if has_conflict:
            conflict_log.append(f"⚠️ CONFLICT: {bullish_count} bullish vs {bearish_count} bearish signals")
            conflict_log.append("Resolution: Prioritizing higher-weight signals")

        # Final direction
        if weighted_score > 25:
            direction = "Bullish"
            signal = "BUY"
            confidence = min(95, int(50 + weighted_score * 0.5))
        elif weighted_score < -25:
            direction = "Bearish"
            signal = "SELL"
            confidence = min(95, int(50 + abs(weighted_score) * 0.5))
        else:
            direction = "Sideways"
            signal = "WAIT"
            confidence = int(max(30, 50 - abs(weighted_score)))

        return {
            "direction": direction,
            "signal": signal,
            "confidence": confidence,
            "weighted_score": float(round(weighted_score, 1)),
            "has_conflict": has_conflict,
            "bullish_signals": bullish_count,
            "bearish_signals": bearish_count,
            "conflict_log": conflict_log,
        }

    def _generate_trade(self, verdict: dict, levels: dict, volatility: dict,
                        price: float, symbol: str) -> dict:
        """Generate final trade setup based on verdict."""
        atr = volatility["atr"]
        expected_move = volatility["expected_move"]
        signal = verdict["signal"]
        confidence = verdict["confidence"]

        step = 100 if "BANK" in symbol.upper() else 50
        strike = round(price / step) * step

        if signal == "BUY":
            side = "CE"
            entry = round(price + atr * 0.1, 2)
            sl = round(max(levels["support_1"], price - atr * 1.5), 2)
            t1 = round(min(levels["resistance_1"], price + expected_move * 0.7), 2)
            t2 = round(levels["resistance_2"], 2)
            t3 = round(price + expected_move * 2, 2)
            ce_strike = strike
            pe_strike = strike - step * 2
        elif signal == "SELL":
            side = "PE"
            entry = round(price - atr * 0.1, 2)
            sl = round(min(levels["resistance_1"], price + atr * 1.5), 2)
            t1 = round(max(levels["support_1"], price - expected_move * 0.7), 2)
            t2 = round(levels["support_2"], 2)
            t3 = round(price - expected_move * 2, 2)
            ce_strike = strike + step * 2
            pe_strike = strike
        else:
            side = "WAIT"
            entry = price
            sl = 0
            t1 = t2 = t3 = 0
            ce_strike = strike
            pe_strike = strike

        risk = abs(entry - sl) if sl else 1
        reward = abs(t1 - entry) if t1 else 0
        rr = round(reward / risk, 1) if risk > 0 else 0

        return {
            "signal": signal,
            "side": side,
            "entry": entry,
            "stop_loss": sl,
            "target_1": t1,
            "target_2": t2,
            "target_3": t3,
            "risk_reward": f"1:{rr}",
            "confidence": confidence,
            "expected_points": float(round(expected_move, 0)),
            "strike": f"{strike} {side}",
            "best_ce": f"{ce_strike} CE",
            "best_pe": f"{pe_strike} PE",
            "position_size": "2-3% capital" if confidence > 75 else "1-2% capital",
        }
