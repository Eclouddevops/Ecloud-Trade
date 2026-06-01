"""
Feature Engineering Module
Prepares features for ML models from technical indicators and market data.
"""
import pandas as pd
import numpy as np


class FeatureEngineer:
    """Creates ML-ready features from stock data with technical indicators."""

    def __init__(self, df: pd.DataFrame):
        """
        Initialize with DataFrame containing OHLCV + technical indicators.

        Args:
            df: DataFrame with all technical indicators calculated
        """
        self.df = df.copy()

    def create_features(self, horizon: int = 1) -> tuple:
        """
        Create feature matrix and target variable.

        Args:
            horizon: Prediction horizon in days (1, 5, or 22)

        Returns:
            Tuple of (features DataFrame, target Series)
        """
        self._add_price_features()
        self._add_momentum_features()
        self._add_volatility_features()
        self._add_volume_features()
        self._add_pattern_features()
        self._add_lag_features()

        # Target: future return direction (1 = up, 0 = down)
        self.df["target"] = (
            self.df["close"].shift(-horizon) > self.df["close"]
        ).astype(int)

        # Replace inf/-inf with NaN, then drop all NaN rows
        self.df = self.df.replace([np.inf, -np.inf], np.nan)
        self.df = self.df.dropna()

        # Define feature columns (exclude OHLCV and target)
        exclude_cols = ["open", "high", "low", "close", "volume", "target"]
        feature_cols = [c for c in self.df.columns if c not in exclude_cols]

        X = self.df[feature_cols]
        y = self.df["target"]

        return X, y

    def _add_price_features(self):
        """Add price-based features."""
        # Returns
        self.df["return_1d"] = self.df["close"].pct_change(1)
        self.df["return_5d"] = self.df["close"].pct_change(5)
        self.df["return_10d"] = self.df["close"].pct_change(10)
        self.df["return_20d"] = self.df["close"].pct_change(20)

        # Price relative to moving averages
        self.df["price_to_sma_50"] = self.df["close"] / self.df["sma_50"] - 1
        self.df["price_to_sma_200"] = self.df["close"] / self.df["sma_200"] - 1
        self.df["price_to_ema_20"] = self.df["close"] / self.df["ema_20"] - 1

        # High-Low range
        self.df["hl_range"] = (self.df["high"] - self.df["low"]) / self.df["close"]

        # Gap (open vs previous close)
        self.df["gap"] = (self.df["open"] - self.df["close"].shift(1)) / self.df[
            "close"
        ].shift(1)

    def _add_momentum_features(self):
        """Add momentum-based features."""
        # RSI derivatives
        self.df["rsi_change"] = self.df["rsi"].diff()
        self.df["rsi_above_50"] = (self.df["rsi"] > 50).astype(int)

        # MACD derivatives
        self.df["macd_above_signal"] = (
            self.df["macd"] > self.df["macd_signal"]
        ).astype(int)
        self.df["macd_hist_change"] = self.df["macd_histogram"].diff()

        # Stochastic
        if "stoch_k" in self.df.columns:
            self.df["stoch_cross"] = (
                (self.df["stoch_k"] > self.df["stoch_d"])
                & (self.df["stoch_k"].shift(1) <= self.df["stoch_d"].shift(1))
            ).astype(int)

    def _add_volatility_features(self):
        """Add volatility-based features."""
        # Bollinger Band position
        bb_range = self.df["bb_upper"] - self.df["bb_lower"]
        self.df["bb_position"] = np.where(
            bb_range != 0,
            (self.df["close"] - self.df["bb_lower"]) / bb_range,
            0.5,
        )

        # ATR as percentage of price
        self.df["atr_pct"] = self.df["atr"] / self.df["close"]

        # Volatility (rolling std of returns)
        self.df["volatility_10d"] = self.df["return_1d"].rolling(10).std()
        self.df["volatility_20d"] = self.df["return_1d"].rolling(20).std()

    def _add_volume_features(self):
        """Add volume-based features."""
        # Volume change
        self.df["volume_change"] = self.df["volume"].pct_change()

        # Volume moving average ratio
        self.df["volume_ma_ratio_5"] = (
            self.df["volume"] / self.df["volume"].rolling(5).mean()
        )

        # Price-volume divergence
        self.df["pv_divergence"] = self.df["return_1d"] * self.df["volume_change"]

    def _add_pattern_features(self):
        """Add candlestick pattern features."""
        # Doji (open ≈ close)
        body = abs(self.df["close"] - self.df["open"])
        hl_range = self.df["high"] - self.df["low"]
        self.df["is_doji"] = (body < 0.1 * hl_range).astype(int)

        # Bullish/Bearish candle
        self.df["is_bullish"] = (self.df["close"] > self.df["open"]).astype(int)

        # Consecutive bullish/bearish days
        self.df["consecutive_bullish"] = (
            self.df["is_bullish"]
            .groupby((self.df["is_bullish"] != self.df["is_bullish"].shift()).cumsum())
            .cumcount()
            + 1
        ) * self.df["is_bullish"]

    def _add_lag_features(self):
        """Add lagged features for time-series context."""
        for lag in [1, 2, 3, 5]:
            self.df[f"rsi_lag_{lag}"] = self.df["rsi"].shift(lag)
            self.df[f"return_lag_{lag}"] = self.df["return_1d"].shift(lag)
            self.df[f"volume_ratio_lag_{lag}"] = self.df["volume_ratio"].shift(lag)

    def get_latest_features(self) -> pd.DataFrame:
        """
        Get the most recent feature row for prediction.

        Returns:
            Single-row DataFrame with all features
        """
        exclude_cols = ["open", "high", "low", "close", "volume", "target"]
        feature_cols = [
            c for c in self.df.columns if c not in exclude_cols and c in self.df.columns
        ]
        result = self.df[feature_cols].iloc[[-1]].copy()
        result = result.replace([np.inf, -np.inf], np.nan)
        result = result.fillna(0)
        return result
