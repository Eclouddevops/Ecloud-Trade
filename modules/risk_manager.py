"""
Risk Management Module
Calculates risk metrics, position sizing, and portfolio risk.
"""
import numpy as np
import pandas as pd


class RiskManager:
    """Calculates risk metrics and position sizing."""

    def calculate_risk_metrics(self, df: pd.DataFrame, current_price: float) -> dict:
        """Calculate comprehensive risk metrics for a stock."""
        returns = df["close"].pct_change().dropna()

        # Volatility
        daily_vol = returns.std()
        annual_vol = daily_vol * np.sqrt(252) * 100

        # ATR percentage
        atr = ((df["high"] - df["low"]).tail(14).mean())
        atr_pct = (atr / current_price) * 100

        # Max Drawdown
        cumulative = (1 + returns).cumprod()
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak
        max_dd = abs(drawdown.min()) * 100

        # Value at Risk (95%)
        var_95 = np.percentile(returns, 5) * 100

        # Beta (vs market - simplified using own volatility)
        beta = annual_vol / 15  # Approximate vs NIFTY ~15% vol

        # Risk Rating
        if atr_pct > 3.5 or annual_vol > 40:
            risk_rating = "VERY HIGH"
        elif atr_pct > 2.5 or annual_vol > 30:
            risk_rating = "HIGH"
        elif atr_pct > 1.5 or annual_vol > 20:
            risk_rating = "MEDIUM"
        else:
            risk_rating = "LOW"

        # Volatility score (0-100)
        vol_score = min(100, int(annual_vol * 2.5))

        return {
            "daily_volatility": round(daily_vol * 100, 2),
            "annual_volatility": round(annual_vol, 2),
            "atr": round(atr, 2),
            "atr_pct": round(atr_pct, 2),
            "max_drawdown": round(max_dd, 2),
            "var_95": round(var_95, 2),
            "beta": round(beta, 2),
            "risk_rating": risk_rating,
            "volatility_score": vol_score,
        }

    def calculate_position_size(self, capital: float, risk_pct: float,
                                 entry: float, stop_loss: float) -> dict:
        """Calculate optimal position size based on risk."""
        risk_amount = capital * (risk_pct / 100)
        risk_per_share = abs(entry - stop_loss)

        if risk_per_share == 0:
            return {"error": "Stop loss equals entry"}

        shares = int(risk_amount / risk_per_share)
        position_value = shares * entry
        max_loss = shares * risk_per_share

        return {
            "shares": shares,
            "position_value": round(position_value, 2),
            "risk_amount": round(risk_amount, 2),
            "max_loss": round(max_loss, 2),
            "capital_used_pct": round((position_value / capital) * 100, 1),
        }
