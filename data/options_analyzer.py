"""
Options Trading Analysis Module
Analyzes NIFTY, BANKNIFTY, and SENSEX for CE/PE option trading recommendations.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import ta


class OptionsAnalyzer:
    """Analyzes index options for CE/PE trading recommendations."""

    def __init__(self):
        self.nifty_symbol = "^NSEI"
        self.sensex_symbol = "^BSESN"
        self.banknifty_symbol = "^NSEBANK"

    def analyze_index_options(self, index_name: str = "NIFTY") -> dict:
        symbol_map = {
            "NIFTY": self.nifty_symbol,
            "SENSEX": self.sensex_symbol,
            "BANKNIFTY": self.banknifty_symbol,
        }
        symbol = symbol_map.get(index_name.upper(), self.nifty_symbol)
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo", interval="1d")
        if df.empty or len(df) < 30:
            # Try longer period if short one fails
            df = ticker.history(period="1y", interval="1d")
        if df.empty or len(df) < 15:
            return {"index": index_name, "error": f"Insufficient data for {index_name}"}

        df.columns = [c.lower() for c in df.columns]
        current_price = df["close"].iloc[-1]

        indicators = self._calc_indicators(df)
        momentum = self._calc_momentum(df)
        volatility = self._calc_volatility(df)
        levels = self._calc_levels(df, current_price)
        rec = self._generate_signal(indicators, momentum, volatility, current_price, levels)

        return {
            "index": index_name.upper(),
            "current_price": round(current_price, 2),
            "timestamp": datetime.now().isoformat(),
            "recommendation": rec,
            "indicators": indicators,
            "momentum": momentum,
            "volatility": volatility,
            "levels": levels,
        }

    def get_all_indices_analysis(self) -> list:
        results = []
        for index in ["NIFTY", "BANKNIFTY", "SENSEX"]:
            try:
                print(f"    Analyzing {index} options...")
                results.append(self.analyze_index_options(index))
            except Exception as e:
                results.append({"index": index, "error": str(e)})
        return results

    def _calc_indicators(self, df):
        close, high, low = df["close"], df["high"], df["low"]
        rsi_val = round(ta.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1], 2)
        macd_ind = ta.trend.MACD(close=close)
        macd_val = round(macd_ind.macd().iloc[-1], 2)
        macd_sig = round(macd_ind.macd_signal().iloc[-1], 2)
        macd_hist = round(macd_ind.macd_diff().iloc[-1], 2)
        ema_9 = round(ta.trend.EMAIndicator(close=close, window=9).ema_indicator().iloc[-1], 2)
        ema_21 = round(ta.trend.EMAIndicator(close=close, window=21).ema_indicator().iloc[-1], 2)
        ema_50 = round(ta.trend.EMAIndicator(close=close, window=50).ema_indicator().iloc[-1], 2)
        tp = (high + low + close) / 3
        vol_sum = df["volume"].rolling(20).sum().iloc[-1]
        vwap = round((tp * df["volume"]).rolling(20).sum().iloc[-1] / vol_sum, 2) if vol_sum > 0 else round(close.iloc[-1], 2)
        bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        bb_upper = round(bb.bollinger_hband().iloc[-1], 2)
        bb_lower = round(bb.bollinger_lband().iloc[-1], 2)
        stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close)
        stoch_k = round(stoch.stoch().iloc[-1], 2)
        adx_ind = ta.trend.ADXIndicator(high=high, low=low, close=close)
        adx_val = round(adx_ind.adx().iloc[-1], 2)
        adx_pos = round(adx_ind.adx_pos().iloc[-1], 2)
        adx_neg = round(adx_ind.adx_neg().iloc[-1], 2)
        atr_val = round(ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=10).average_true_range().iloc[-1], 2)
        cur = close.iloc[-1]
        return {
            "rsi": rsi_val,
            "rsi_signal": "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral",
            "macd": macd_val, "macd_signal_line": macd_sig, "macd_histogram": macd_hist,
            "macd_crossover": "Bullish" if macd_val > macd_sig else "Bearish",
            "ema_9": ema_9, "ema_21": ema_21, "ema_50": ema_50,
            "ema_trend": "Bullish" if ema_9 > ema_21 else "Bearish",
            "vwap": vwap, "price_vs_vwap": "Above" if cur > vwap else "Below",
            "bollinger_upper": bb_upper, "bollinger_lower": bb_lower,
            "stochastic_k": stoch_k,
            "stochastic_signal": "Overbought" if stoch_k > 80 else "Oversold" if stoch_k < 20 else "Neutral",
            "adx": adx_val, "adx_pos": adx_pos, "adx_neg": adx_neg,
            "trend_strength": "Strong" if adx_val > 25 else "Weak",
            "atr": atr_val,
            "price_above_ema9": bool(cur > ema_9),
            "price_above_ema21": bool(cur > ema_21),
            "price_above_vwap": bool(cur > vwap),
        }

    def _calc_momentum(self, df):
        close = df["close"]
        n = len(close)
        ret_1d = round(((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]) * 100, 2) if n >= 2 else 0
        ret_3d = round(((close.iloc[-1] - close.iloc[-4]) / close.iloc[-4]) * 100, 2) if n >= 5 else ret_1d
        ret_5d = round(((close.iloc[-1] - close.iloc[-6]) / close.iloc[-6]) * 100, 2) if n >= 7 else ret_3d
        daily_changes = close.diff().tail(min(10, n))
        cons_up, cons_down = 0, 0
        for ch in reversed(daily_changes.values):
            if ch > 0:
                if cons_down > 0: break
                cons_up += 1
            elif ch < 0:
                if cons_up > 0: break
                cons_down += 1
            else:
                break
        gap = round(((df["open"].iloc[-1] - close.iloc[-2]) / close.iloc[-2]) * 100, 2) if n >= 2 else 0
        candle = "Bullish" if close.iloc[-1] > df["open"].iloc[-1] else "Bearish"
        return {
            "return_1d": ret_1d, "return_3d": ret_3d, "return_5d": ret_5d,
            "consecutive_up_days": cons_up, "consecutive_down_days": cons_down,
            "gap_pct": gap, "last_candle": candle,
            "intraday_bias": "Bullish" if ret_1d > 0.3 else "Bearish" if ret_1d < -0.3 else "Neutral",
        }

    def _calc_volatility(self, df):
        close = df["close"]
        returns = close.pct_change().dropna()
        n = len(returns)
        hv_10 = round(returns.tail(min(10, n)).std() * np.sqrt(252) * 100, 2) if n >= 2 else 15.0
        hv_20 = round(returns.tail(min(20, n)).std() * np.sqrt(252) * 100, 2) if n >= 2 else 15.0
        daily_range = round(((df["high"] - df["low"]) / df["close"] * 100).tail(min(10, len(df))).mean(), 2)
        cur = close.iloc[-1]
        daily_move = round(cur * (hv_10 / 100) / np.sqrt(252), 0)
        weekly_move = round(cur * (hv_10 / 100) / np.sqrt(52), 0)
        return {
            "hv_10": hv_10, "hv_20": hv_20,
            "avg_daily_range_pct": daily_range,
            "volatility_regime": "High" if hv_10 > 18 else "Low" if hv_10 < 10 else "Normal",
            "expected_daily_move": daily_move,
            "expected_weekly_move": weekly_move,
        }

    def _calc_levels(self, df, current_price):
        n = len(df)
        if n < 2:
            step = 50
            atm = round(current_price / step) * step
            return {"pivot": round(current_price, 2), "resistance_1": round(current_price * 1.01, 2),
                    "resistance_2": round(current_price * 1.02, 2), "support_1": round(current_price * 0.99, 2),
                    "support_2": round(current_price * 0.98, 2), "atm_strike": atm,
                    "otm_ce_strike": atm + 100, "otm_pe_strike": atm - 100,
                    "day_high": round(current_price, 2), "day_low": round(current_price, 2)}
        prev_h = df["high"].iloc[-2]
        prev_l = df["low"].iloc[-2]
        prev_c = df["close"].iloc[-2]
        pivot = (prev_h + prev_l + prev_c) / 3
        r1 = 2 * pivot - prev_l
        r2 = pivot + (prev_h - prev_l)
        s1 = 2 * pivot - prev_h
        s2 = pivot - (prev_h - prev_l)
        step = 50
        atm = round(current_price / step) * step
        return {
            "pivot": round(pivot, 2), "resistance_1": round(r1, 2), "resistance_2": round(r2, 2),
            "support_1": round(s1, 2), "support_2": round(s2, 2),
            "atm_strike": atm, "otm_ce_strike": atm + 100, "otm_pe_strike": atm - 100,
            "day_high": round(df["high"].iloc[-1], 2), "day_low": round(df["low"].iloc[-1], 2),
        }

    def _generate_signal(self, ind, mom, vol, price, levels):
        score = 0
        reasons = []

        # EMA Trend
        if ind["ema_trend"] == "Bullish":
            score += 2; reasons.append("EMA 9 > EMA 21 (Bullish)")
        else:
            score -= 2; reasons.append("EMA 9 < EMA 21 (Bearish)")

        # VWAP
        if ind["price_vs_vwap"] == "Above":
            score += 1.5; reasons.append("Price above VWAP")
        else:
            score -= 1.5; reasons.append("Price below VWAP")

        # RSI
        rsi = ind["rsi"]
        if 60 < rsi < 75:
            score += 1.5; reasons.append(f"RSI {rsi} bullish momentum")
        elif rsi > 75:
            score -= 0.5; reasons.append(f"RSI {rsi} overbought")
        elif 25 < rsi < 40:
            score -= 1.5; reasons.append(f"RSI {rsi} bearish momentum")
        elif rsi < 25:
            score += 0.5; reasons.append(f"RSI {rsi} oversold bounce")

        # MACD
        if ind["macd_crossover"] == "Bullish" and ind["macd_histogram"] > 0:
            score += 2; reasons.append("MACD bullish + positive histogram")
        elif ind["macd_crossover"] == "Bearish" and ind["macd_histogram"] < 0:
            score -= 2; reasons.append("MACD bearish + negative histogram")
        elif ind["macd_crossover"] == "Bullish":
            score += 1; reasons.append("MACD bullish crossover")
        else:
            score -= 1; reasons.append("MACD bearish crossover")

        # Stochastic
        if ind["stochastic_signal"] == "Oversold":
            score += 1; reasons.append("Stochastic oversold (bounce)")
        elif ind["stochastic_signal"] == "Overbought":
            score -= 1; reasons.append("Stochastic overbought (drop)")

        # ADX
        if ind["adx"] > 25:
            if ind["adx_pos"] > ind["adx_neg"]:
                score += 1; reasons.append("Strong uptrend (ADX)")
            else:
                score -= 1; reasons.append("Strong downtrend (ADX)")

        # Momentum
        if mom["return_1d"] > 0.5:
            score += 1.5; reasons.append(f"Bullish momentum +{mom['return_1d']}%")
        elif mom["return_1d"] < -0.5:
            score -= 1.5; reasons.append(f"Bearish momentum {mom['return_1d']}%")

        # Bollinger
        if price > ind["bollinger_upper"]:
            score -= 1; reasons.append("Above upper Bollinger")
        elif price < ind["bollinger_lower"]:
            score += 1; reasons.append("Below lower Bollinger")

        # Determine side
        if score >= 4:
            side, confidence = "CE", "High"
        elif score >= 2:
            side, confidence = "CE", "Medium"
        elif score <= -4:
            side, confidence = "PE", "High"
        elif score <= -2:
            side, confidence = "PE", "Medium"
        else:
            side, confidence = "NEUTRAL", "Low"

        action = f"BUY {side}" if side != "NEUTRAL" else "NO TRADE - WAIT"
        strike = levels["atm_strike"]
        target = levels["resistance_1"] if side == "CE" else levels["support_1"]
        sl = levels["support_1"] if side == "CE" else levels["resistance_1"]

        return {
            "side": side,
            "action": action,
            "confidence": confidence,
            "score": round(score, 1),
            "suggested_strike": strike,
            "target_level": round(target, 2),
            "stoploss_level": round(sl, 2),
            "expected_move": vol["expected_daily_move"],
            "risk_reward": "1:2" if confidence == "High" else "1:1.5",
            "position_sizing": "2-3% capital" if confidence == "High" else "1-2% capital",
            "exit_strategy": "Exit at target OR 30% premium loss",
            "reasons": reasons,
        }
