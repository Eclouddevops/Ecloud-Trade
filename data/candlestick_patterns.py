"""
Candlestick Pattern Detection Module
Detects major candlestick patterns and generates signals.
"""
import pandas as pd
import numpy as np


class CandlestickPatternDetector:
    """Detects candlestick patterns from OHLC data."""

    def __init__(self, df: pd.DataFrame):
        """
        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close']
        """
        self.df = df.copy()
        self.patterns = []

    def detect_all(self) -> list:
        """Detect all patterns on the latest candles. Returns list of detected patterns."""
        self.patterns = []
        self._detect_hammer()
        self._detect_shooting_star()
        self._detect_three_white_soldiers()
        self._detect_three_black_crows()
        self._detect_green_marubozu()
        self._detect_red_marubozu()
        self._detect_bullish_engulfing()
        self._detect_bearish_engulfing()
        self._detect_doji()
        self._detect_morning_star()
        self._detect_evening_star()
        return self.patterns

    def _body(self, i):
        return abs(self.df["close"].iloc[i] - self.df["open"].iloc[i])

    def _range(self, i):
        return self.df["high"].iloc[i] - self.df["low"].iloc[i]

    def _is_bullish(self, i):
        return self.df["close"].iloc[i] > self.df["open"].iloc[i]

    def _is_bearish(self, i):
        return self.df["close"].iloc[i] < self.df["open"].iloc[i]

    def _upper_shadow(self, i):
        if self._is_bullish(i):
            return self.df["high"].iloc[i] - self.df["close"].iloc[i]
        return self.df["high"].iloc[i] - self.df["open"].iloc[i]

    def _lower_shadow(self, i):
        if self._is_bullish(i):
            return self.df["open"].iloc[i] - self.df["low"].iloc[i]
        return self.df["close"].iloc[i] - self.df["low"].iloc[i]

    def _in_downtrend(self, i, lookback=5):
        if i < lookback:
            return False
        return self.df["close"].iloc[i - lookback] > self.df["close"].iloc[i - 1]

    def _in_uptrend(self, i, lookback=5):
        if i < lookback:
            return False
        return self.df["close"].iloc[i - lookback] < self.df["close"].iloc[i - 1]

    def _detect_hammer(self):
        i = -1
        rng = self._range(i)
        if rng == 0:
            return
        body = self._body(i)
        lower = self._lower_shadow(i)
        upper = self._upper_shadow(i)
        if (lower >= 2 * body and upper <= body * 0.3 and
                body / rng < 0.35 and self._in_downtrend(len(self.df) + i)):
            conf = min(90, int(60 + (lower / rng) * 30))
            self.patterns.append({
                "pattern": "Hammer",
                "signal": "BUY",
                "type": "Bullish Reversal",
                "confidence": conf,
                "description": "Small body, long lower wick after downtrend. Market reversal likely.",
            })

    def _detect_shooting_star(self):
        i = -1
        rng = self._range(i)
        if rng == 0:
            return
        body = self._body(i)
        upper = self._upper_shadow(i)
        lower = self._lower_shadow(i)
        if (upper >= 2 * body and lower <= body * 0.3 and
                body / rng < 0.35 and self._in_uptrend(len(self.df) + i)):
            conf = min(90, int(60 + (upper / rng) * 30))
            self.patterns.append({
                "pattern": "Shooting Star",
                "signal": "SELL",
                "type": "Bearish Reversal",
                "confidence": conf,
                "description": "Small body, long upper shadow after uptrend. Reversal downward likely.",
            })

    def _detect_three_white_soldiers(self):
        if len(self.df) < 4:
            return
        c1 = self._is_bullish(-3) and self._body(-3) > self._range(-3) * 0.5
        c2 = self._is_bullish(-2) and self._body(-2) > self._range(-2) * 0.5
        c3 = self._is_bullish(-1) and self._body(-1) > self._range(-1) * 0.5
        higher = (self.df["close"].iloc[-1] > self.df["close"].iloc[-2] >
                  self.df["close"].iloc[-3])
        if c1 and c2 and c3 and higher:
            self.patterns.append({
                "pattern": "Three White Soldiers",
                "signal": "STRONG BUY",
                "type": "Strong Bullish",
                "confidence": 85,
                "description": "Three consecutive bullish candles, each closing higher. Strong uptrend.",
            })

    def _detect_three_black_crows(self):
        if len(self.df) < 4:
            return
        c1 = self._is_bearish(-3) and self._body(-3) > self._range(-3) * 0.5
        c2 = self._is_bearish(-2) and self._body(-2) > self._range(-2) * 0.5
        c3 = self._is_bearish(-1) and self._body(-1) > self._range(-1) * 0.5
        lower = (self.df["close"].iloc[-1] < self.df["close"].iloc[-2] <
                 self.df["close"].iloc[-3])
        if c1 and c2 and c3 and lower:
            self.patterns.append({
                "pattern": "Three Black Crows",
                "signal": "STRONG SELL",
                "type": "Strong Bearish",
                "confidence": 85,
                "description": "Three consecutive bearish candles, each closing lower. Strong downtrend.",
            })

    def _detect_green_marubozu(self):
        i = -1
        rng = self._range(i)
        if rng == 0:
            return
        body = self._body(i)
        if (self._is_bullish(i) and body / rng > 0.9 and
                self._in_downtrend(len(self.df) + i)):
            self.patterns.append({
                "pattern": "Green Marubozu",
                "signal": "BUY",
                "type": "Bullish",
                "confidence": 75,
                "description": "Large bullish candle with no wicks. Buyers in full control.",
            })

    def _detect_red_marubozu(self):
        i = -1
        rng = self._range(i)
        if rng == 0:
            return
        body = self._body(i)
        if (self._is_bearish(i) and body / rng > 0.9 and
                self._in_uptrend(len(self.df) + i)):
            self.patterns.append({
                "pattern": "Red Marubozu",
                "signal": "SELL",
                "type": "Bearish",
                "confidence": 75,
                "description": "Large bearish candle with no wicks. Sellers in full control.",
            })

    def _detect_bullish_engulfing(self):
        if len(self.df) < 3:
            return
        prev_bearish = self._is_bearish(-2)
        curr_bullish = self._is_bullish(-1)
        engulfs = (self.df["open"].iloc[-1] <= self.df["close"].iloc[-2] and
                   self.df["close"].iloc[-1] >= self.df["open"].iloc[-2])
        if prev_bearish and curr_bullish and engulfs:
            self.patterns.append({
                "pattern": "Bullish Engulfing",
                "signal": "BUY",
                "type": "Bullish Reversal",
                "confidence": 78,
                "description": "Green candle fully engulfs previous red candle. Trend reversal upward.",
            })

    def _detect_bearish_engulfing(self):
        if len(self.df) < 3:
            return
        prev_bullish = self._is_bullish(-2)
        curr_bearish = self._is_bearish(-1)
        engulfs = (self.df["open"].iloc[-1] >= self.df["close"].iloc[-2] and
                   self.df["close"].iloc[-1] <= self.df["open"].iloc[-2])
        if prev_bullish and curr_bearish and engulfs:
            self.patterns.append({
                "pattern": "Bearish Engulfing",
                "signal": "SELL",
                "type": "Bearish Reversal",
                "confidence": 78,
                "description": "Red candle fully engulfs previous green candle. Trend reversal downward.",
            })

    def _detect_doji(self):
        i = -1
        rng = self._range(i)
        if rng == 0:
            return
        body = self._body(i)
        if body / rng < 0.05:
            self.patterns.append({
                "pattern": "Doji",
                "signal": "HOLD",
                "type": "Indecision",
                "confidence": 60,
                "description": "Open equals close. Market indecision - wait for confirmation.",
            })

    def _detect_morning_star(self):
        if len(self.df) < 4:
            return
        first_bear = self._is_bearish(-3) and self._body(-3) > self._range(-3) * 0.5
        small_body = self._body(-2) < self._range(-2) * 0.3
        third_bull = self._is_bullish(-1) and self._body(-1) > self._range(-1) * 0.5
        closes_above = self.df["close"].iloc[-1] > (self.df["open"].iloc[-3] + self.df["close"].iloc[-3]) / 2
        if first_bear and small_body and third_bull and closes_above:
            self.patterns.append({
                "pattern": "Morning Star",
                "signal": "BUY",
                "type": "Bullish Reversal",
                "confidence": 80,
                "description": "Three-candle reversal pattern. Strong bullish signal.",
            })

    def _detect_evening_star(self):
        if len(self.df) < 4:
            return
        first_bull = self._is_bullish(-3) and self._body(-3) > self._range(-3) * 0.5
        small_body = self._body(-2) < self._range(-2) * 0.3
        third_bear = self._is_bearish(-1) and self._body(-1) > self._range(-1) * 0.5
        closes_below = self.df["close"].iloc[-1] < (self.df["open"].iloc[-3] + self.df["close"].iloc[-3]) / 2
        if first_bull and small_body and third_bear and closes_below:
            self.patterns.append({
                "pattern": "Evening Star",
                "signal": "SELL",
                "type": "Bearish Reversal",
                "confidence": 80,
                "description": "Three-candle reversal pattern. Strong bearish signal.",
            })
