"""
Deep Stock Analysis Module
Generates comprehensive AI-powered stock research reports.
"""
import yfinance as yf
import pandas as pd
import numpy as np
import ta
from datetime import datetime
from data.candlestick_patterns import CandlestickPatternDetector
from modules.pivot_analysis import PivotAnalyzer
from modules.risk_manager import RiskManager
from modules.company_fundamentals import CompanyFundamentals
from modules.news_intelligence import NewsIntelligence


class DeepStockAnalyzer:
    """Generates Bloomberg-style deep analysis reports."""

    def analyze(self, symbol: str) -> dict:
        """Generate complete deep analysis for a stock."""
        ticker = yf.Ticker(f"{symbol}.NS")
        df = ticker.history(period="1y")
        if df.empty:
            return {"symbol": symbol, "error": "No data available"}

        df.columns = [c.lower() for c in df.columns]
        info = ticker.info
        price = df["close"].iloc[-1]

        # Company Overview
        company = {
            "name": info.get("longName", symbol),
            "symbol": symbol,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "roe": info.get("returnOnEquity"),
            "debt_equity": info.get("debtToEquity"),
            "dividend_yield": info.get("dividendYield"),
            "eps": info.get("trailingEps"),
            "beta": info.get("beta"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
        }

        # Price Performance
        performance = self._calc_performance(df, price)

        # Technical Analysis
        technical = self._calc_technical(df)

        # Candlestick Patterns
        detector = CandlestickPatternDetector(df)
        patterns = detector.detect_all()

        # Pivot Points
        pivot_analyzer = PivotAnalyzer()
        pivots = pivot_analyzer.calculate_pivots(
            df["high"].iloc[-2], df["low"].iloc[-2], df["close"].iloc[-2]
        )

        # Risk
        risk_mgr = RiskManager()
        risk = risk_mgr.calculate_risk_metrics(df, price)

        # Scores
        tech_score = self._calc_tech_score(technical)
        fund_score = self._calc_fund_score(info)
        risk_score = 100 - risk["volatility_score"]
        overall_score = int(tech_score * 0.4 + fund_score * 0.3 + risk_score * 0.3)

        # Final Verdict
        if overall_score >= 75:
            verdict = "STRONG BUY"
        elif overall_score >= 60:
            verdict = "BUY"
        elif overall_score >= 40:
            verdict = "HOLD"
        elif overall_score >= 25:
            verdict = "SELL"
        else:
            verdict = "STRONG SELL"

        return {
            "symbol": symbol,
            "price": round(price, 2),
            "timestamp": datetime.now().isoformat(),
            "company": company,
            "performance": performance,
            "technical": technical,
            "patterns": patterns,
            "pivots": pivots,
            "risk": risk,
            "scores": {
                "technical": tech_score,
                "fundamental": fund_score,
                "risk": risk_score,
                "overall": overall_score,
            },
            "verdict": verdict,
        }

    def _calc_performance(self, df, price):
        close = df["close"]
        perf = {}
        periods = {"1d": 1, "1w": 5, "1m": 22, "3m": 66, "6m": 132, "1y": 252}
        for name, days in periods.items():
            if len(close) > days:
                prev = close.iloc[-(days + 1)]
                perf[name] = round(((price - prev) / prev) * 100, 2)
            else:
                perf[name] = None
        return perf

    def _calc_technical(self, df):
        close, high, low = df["close"], df["high"], df["low"]
        rsi = ta.momentum.RSIIndicator(close=close).rsi().iloc[-1]
        macd_ind = ta.trend.MACD(close=close)
        macd = macd_ind.macd().iloc[-1]
        macd_sig = macd_ind.macd_signal().iloc[-1]
        ema_20 = ta.trend.EMAIndicator(close=close, window=20).ema_indicator().iloc[-1]
        ema_50 = ta.trend.EMAIndicator(close=close, window=50).ema_indicator().iloc[-1]
        sma_200 = ta.trend.SMAIndicator(close=close, window=200).sma_indicator().iloc[-1]
        bb = ta.volatility.BollingerBands(close=close)
        adx = ta.trend.ADXIndicator(high=high, low=low, close=close).adx().iloc[-1]
        cur = close.iloc[-1]

        trend = "Bullish" if cur > ema_20 > ema_50 else "Bearish" if cur < ema_20 < ema_50 else "Sideways"
        macd_signal = "Bullish" if macd > macd_sig else "Bearish"

        return {
            "rsi": round(rsi, 2),
            "rsi_signal": "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral",
            "macd": round(macd, 2),
            "macd_signal": macd_signal,
            "ema_20": round(ema_20, 2),
            "ema_50": round(ema_50, 2),
            "sma_200": round(sma_200, 2),
            "adx": round(adx, 2),
            "trend": trend,
            "above_200sma": bool(cur > sma_200),
        }

    def _calc_tech_score(self, tech):
        score = 50
        if tech["trend"] == "Bullish": score += 15
        elif tech["trend"] == "Bearish": score -= 15
        if tech["macd_signal"] == "Bullish": score += 10
        else: score -= 10
        if tech["rsi"] < 30: score += 10
        elif tech["rsi"] > 70: score -= 10
        if tech["above_200sma"]: score += 10
        else: score -= 10
        if tech["adx"] > 25: score += 5
        return max(0, min(100, score))

    def _calc_fund_score(self, info):
        score = 50
        pe = info.get("trailingPE")
        if pe and pe < 20: score += 10
        elif pe and pe > 40: score -= 10
        roe = info.get("returnOnEquity")
        if roe and roe > 0.15: score += 15
        elif roe and roe < 0.05: score -= 10
        de = info.get("debtToEquity")
        if de and de < 50: score += 10
        elif de and de > 150: score -= 15
        margin = info.get("profitMargins")
        if margin and margin > 0.15: score += 10
        elif margin and margin < 0.05: score -= 10
        return max(0, min(100, score))
