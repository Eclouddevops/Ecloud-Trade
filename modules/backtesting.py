"""
Backtesting Engine Module
Backtests trading strategies on historical data.
"""
import pandas as pd
import numpy as np
import ta


class BacktestEngine:
    """Backtests various trading strategies."""

    def __init__(self, df: pd.DataFrame, capital: float = 100000):
        self.df = df.copy()
        self.initial_capital = capital
        self.results = {}

    def run_ema_cross(self, fast: int = 20, slow: int = 50) -> dict:
        """Backtest EMA crossover strategy."""
        df = self.df.copy()
        df["ema_fast"] = ta.trend.EMAIndicator(close=df["close"], window=fast).ema_indicator()
        df["ema_slow"] = ta.trend.EMAIndicator(close=df["close"], window=slow).ema_indicator()
        df = df.dropna()

        # Signals
        df["signal"] = 0
        df.loc[df["ema_fast"] > df["ema_slow"], "signal"] = 1
        df.loc[df["ema_fast"] < df["ema_slow"], "signal"] = -1
        df["position"] = df["signal"].shift(1)

        return self._calculate_metrics(df, f"EMA Cross ({fast}/{slow})")

    def run_rsi_strategy(self, buy_level: int = 30, sell_level: int = 70) -> dict:
        """Backtest RSI strategy."""
        df = self.df.copy()
        df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
        df = df.dropna()

        df["signal"] = 0
        df.loc[df["rsi"] < buy_level, "signal"] = 1
        df.loc[df["rsi"] > sell_level, "signal"] = -1
        df["position"] = df["signal"].shift(1).fillna(0)

        return self._calculate_metrics(df, f"RSI ({buy_level}/{sell_level})")

    def run_macd_strategy(self) -> dict:
        """Backtest MACD crossover strategy."""
        df = self.df.copy()
        macd_ind = ta.trend.MACD(close=df["close"])
        df["macd"] = macd_ind.macd()
        df["macd_signal"] = macd_ind.macd_signal()
        df = df.dropna()

        df["signal"] = 0
        df.loc[df["macd"] > df["macd_signal"], "signal"] = 1
        df.loc[df["macd"] < df["macd_signal"], "signal"] = -1
        df["position"] = df["signal"].shift(1)

        return self._calculate_metrics(df, "MACD Crossover")

    def _calculate_metrics(self, df: pd.DataFrame, strategy_name: str) -> dict:
        """Calculate backtest performance metrics."""
        df["returns"] = df["close"].pct_change()
        df["strategy_returns"] = df["returns"] * df["position"]
        df = df.dropna()

        if len(df) == 0:
            return {"strategy": strategy_name, "error": "Insufficient data"}

        # Trades
        df["trade_change"] = df["position"].diff().abs()
        total_trades = int(df["trade_change"].sum() / 2)

        # Returns
        cumulative = (1 + df["strategy_returns"]).cumprod()
        total_return = (cumulative.iloc[-1] - 1) * 100 if len(cumulative) > 0 else 0

        # Win rate
        winning = df[df["strategy_returns"] > 0]["strategy_returns"]
        losing = df[df["strategy_returns"] < 0]["strategy_returns"]
        win_rate = len(winning) / (len(winning) + len(losing)) * 100 if (len(winning) + len(losing)) > 0 else 0

        # Sharpe Ratio (annualized)
        mean_ret = df["strategy_returns"].mean()
        std_ret = df["strategy_returns"].std()
        sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0

        # Max Drawdown
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak
        max_dd = drawdown.min() * 100

        # CAGR
        days = len(df)
        years = days / 252
        final_val = self.initial_capital * cumulative.iloc[-1]
        cagr = ((final_val / self.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

        # Profit Factor
        gross_profit = winning.sum()
        gross_loss = abs(losing.sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        return {
            "strategy": strategy_name,
            "total_trades": total_trades,
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(win_rate, 1),
            "total_return_pct": round(total_return, 2),
            "cagr": round(cagr, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd, 2),
            "profit_factor": round(profit_factor, 2),
            "final_capital": round(final_val, 0),
        }

    def run_all(self) -> list:
        """Run all strategies and return comparison."""
        results = []
        results.append(self.run_ema_cross(20, 50))
        results.append(self.run_rsi_strategy(30, 70))
        results.append(self.run_macd_strategy())
        return results
