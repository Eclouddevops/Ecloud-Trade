"""
Technical Indicators Module
Calculates all major technical indicators for stock analysis.
"""
import pandas as pd
import numpy as np
import ta
from config.settings import (
    RSI_PERIOD,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    EMA_SHORT,
    EMA_LONG,
    SMA_200,
    BOLLINGER_PERIOD,
    BOLLINGER_STD,
    ATR_PERIOD,
)


class TechnicalIndicators:
    """Calculates technical indicators for stock data."""

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with OHLCV DataFrame.

        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        """
        self.df = df.copy()

    def calculate_all(self) -> pd.DataFrame:
        """Calculate all technical indicators and return enriched DataFrame."""
        self._calculate_rsi()
        self._calculate_macd()
        self._calculate_ema()
        self._calculate_sma()
        self._calculate_bollinger_bands()
        self._calculate_atr()
        self._calculate_volume_indicators()
        self._calculate_stochastic()
        self._calculate_adx()
        self._calculate_obv()
        return self.df

    def _calculate_rsi(self):
        """Calculate Relative Strength Index."""
        self.df["rsi"] = ta.momentum.RSIIndicator(
            close=self.df["close"], window=RSI_PERIOD
        ).rsi()

    def _calculate_macd(self):
        """Calculate MACD, Signal Line, and Histogram."""
        macd_indicator = ta.trend.MACD(
            close=self.df["close"],
            window_slow=MACD_SLOW,
            window_fast=MACD_FAST,
            window_sign=MACD_SIGNAL,
        )
        self.df["macd"] = macd_indicator.macd()
        self.df["macd_signal"] = macd_indicator.macd_signal()
        self.df["macd_histogram"] = macd_indicator.macd_diff()

    def _calculate_ema(self):
        """Calculate Exponential Moving Averages."""
        self.df["ema_20"] = ta.trend.EMAIndicator(
            close=self.df["close"], window=EMA_SHORT
        ).ema_indicator()
        self.df["ema_50"] = ta.trend.EMAIndicator(
            close=self.df["close"], window=EMA_LONG
        ).ema_indicator()

    def _calculate_sma(self):
        """Calculate Simple Moving Averages."""
        self.df["sma_50"] = ta.trend.SMAIndicator(
            close=self.df["close"], window=50
        ).sma_indicator()
        self.df["sma_200"] = ta.trend.SMAIndicator(
            close=self.df["close"], window=SMA_200
        ).sma_indicator()

    def _calculate_bollinger_bands(self):
        """Calculate Bollinger Bands."""
        bb = ta.volatility.BollingerBands(
            close=self.df["close"],
            window=BOLLINGER_PERIOD,
            window_dev=BOLLINGER_STD,
        )
        self.df["bb_upper"] = bb.bollinger_hband()
        self.df["bb_middle"] = bb.bollinger_mavg()
        self.df["bb_lower"] = bb.bollinger_lband()
        self.df["bb_width"] = bb.bollinger_wband()

    def _calculate_atr(self):
        """Calculate Average True Range."""
        self.df["atr"] = ta.volatility.AverageTrueRange(
            high=self.df["high"],
            low=self.df["low"],
            close=self.df["close"],
            window=ATR_PERIOD,
        ).average_true_range()

    def _calculate_volume_indicators(self):
        """Calculate volume-based indicators."""
        self.df["volume_sma_20"] = self.df["volume"].rolling(window=20).mean()
        self.df["volume_ratio"] = self.df["volume"] / self.df["volume_sma_20"]

    def _calculate_stochastic(self):
        """Calculate Stochastic Oscillator."""
        stoch = ta.momentum.StochasticOscillator(
            high=self.df["high"],
            low=self.df["low"],
            close=self.df["close"],
            window=14,
            smooth_window=3,
        )
        self.df["stoch_k"] = stoch.stoch()
        self.df["stoch_d"] = stoch.stoch_signal()

    def _calculate_adx(self):
        """Calculate Average Directional Index."""
        adx = ta.trend.ADXIndicator(
            high=self.df["high"],
            low=self.df["low"],
            close=self.df["close"],
            window=14,
        )
        self.df["adx"] = adx.adx()
        self.df["adx_pos"] = adx.adx_pos()
        self.df["adx_neg"] = adx.adx_neg()

    def _calculate_obv(self):
        """Calculate On-Balance Volume."""
        self.df["obv"] = ta.volume.OnBalanceVolumeIndicator(
            close=self.df["close"], volume=self.df["volume"]
        ).on_balance_volume()

    def get_support_resistance(self, lookback: int = 60) -> dict:
        """
        Calculate support and resistance levels using pivot points.

        Args:
            lookback: Number of periods to look back

        Returns:
            Dictionary with support and resistance levels
        """
        recent = self.df.tail(lookback)
        high = recent["high"].max()
        low = recent["low"].min()
        close = recent["close"].iloc[-1]

        # Pivot Point calculation
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)

        return {
            "pivot": round(pivot, 2),
            "resistance_1": round(r1, 2),
            "resistance_2": round(r2, 2),
            "support_1": round(s1, 2),
            "support_2": round(s2, 2),
            "52_week_high": round(self.df["high"].tail(252).max(), 2),
            "52_week_low": round(self.df["low"].tail(252).min(), 2),
        }

    def get_indicator_summary(self) -> dict:
        """
        Get a summary of current indicator values.

        Returns:
            Dictionary with latest indicator values and signals
        """
        latest = self.df.iloc[-1]
        prev = self.df.iloc[-2]

        # RSI Signal
        rsi_signal = "Neutral"
        if latest["rsi"] > 70:
            rsi_signal = "Overbought"
        elif latest["rsi"] < 30:
            rsi_signal = "Oversold"

        # MACD Signal
        macd_signal = "Neutral"
        if latest["macd"] > latest["macd_signal"] and prev["macd"] <= prev["macd_signal"]:
            macd_signal = "Bullish Crossover"
        elif latest["macd"] < latest["macd_signal"] and prev["macd"] >= prev["macd_signal"]:
            macd_signal = "Bearish Crossover"
        elif latest["macd"] > latest["macd_signal"]:
            macd_signal = "Bullish"
        else:
            macd_signal = "Bearish"

        # Moving Average Signal
        ma_signal = "Neutral"
        if latest["close"] > latest["sma_50"] > latest["sma_200"]:
            ma_signal = "Strong Bullish"
        elif latest["close"] > latest["sma_50"]:
            ma_signal = "Bullish"
        elif latest["close"] < latest["sma_50"] < latest["sma_200"]:
            ma_signal = "Strong Bearish"
        elif latest["close"] < latest["sma_50"]:
            ma_signal = "Bearish"

        # Bollinger Band Signal
        bb_signal = "Neutral"
        if latest["close"] > latest["bb_upper"]:
            bb_signal = "Overbought"
        elif latest["close"] < latest["bb_lower"]:
            bb_signal = "Oversold"

        # ADX Trend Strength
        trend_strength = "Weak"
        if latest["adx"] > 40:
            trend_strength = "Very Strong"
        elif latest["adx"] > 25:
            trend_strength = "Strong"
        elif latest["adx"] > 20:
            trend_strength = "Moderate"

        return {
            "rsi": round(latest["rsi"], 2),
            "rsi_signal": rsi_signal,
            "macd": round(latest["macd"], 4),
            "macd_signal_line": round(latest["macd_signal"], 4),
            "macd_histogram": round(latest["macd_histogram"], 4),
            "macd_signal": macd_signal,
            "ema_20": round(latest["ema_20"], 2),
            "ema_50": round(latest["ema_50"], 2),
            "sma_50": round(latest["sma_50"], 2),
            "sma_200": round(latest["sma_200"], 2),
            "ma_signal": ma_signal,
            "bb_upper": round(latest["bb_upper"], 2),
            "bb_lower": round(latest["bb_lower"], 2),
            "bb_signal": bb_signal,
            "atr": round(latest["atr"], 2),
            "adx": round(latest["adx"], 2),
            "trend_strength": trend_strength,
            "volume_ratio": round(latest["volume_ratio"], 2),
        }
