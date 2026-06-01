"""
Daily Market Overview Module
Fetches live market summary data: indices, top gainers/losers, sector performance.
"""
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


class MarketOverview:
    """Fetches daily market overview data for Indian stock market."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def get_market_indices(self) -> dict:
        """Fetch current values of major Indian market indices."""
        indices = {
            "NIFTY_50": "^NSEI",
            "SENSEX": "^BSESN",
            "NIFTY_BANK": "^NSEBANK",
            "NIFTY_IT": "^CNXIT",
        }

        result = {}
        for name, symbol in indices.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                if len(hist) >= 2:
                    current = hist["Close"].iloc[-1]
                    prev = hist["Close"].iloc[-2]
                    change = current - prev
                    change_pct = (change / prev) * 100
                    result[name] = {
                        "value": round(current, 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                    }
                elif len(hist) == 1:
                    result[name] = {
                        "value": round(hist["Close"].iloc[-1], 2),
                        "change": 0,
                        "change_pct": 0,
                    }
            except Exception as e:
                result[name] = {"value": 0, "change": 0, "change_pct": 0, "error": str(e)}

        return result

    def get_top_gainers_losers(self, stocks: list = None) -> dict:
        """
        Get top gainers and losers from a stock list.

        Args:
            stocks: List of stock symbols. Uses NIFTY 50 components if None.

        Returns:
            Dictionary with gainers and losers lists
        """
        if stocks is None:
            stocks = [
                "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
                "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK", "LT",
                "HINDUNILVR", "BAJFINANCE", "MARUTI", "AXISBANK",
                "SUNPHARMA", "TITAN", "WIPRO",
                "ADANIENT", "NTPC", "POWERGRID", "ONGC",
                "TATASTEEL", "HCLTECH", "ULTRACEMCO",
            ]

        changes = []
        for symbol in stocks:
            try:
                ticker = yf.Ticker(f"{symbol}.NS")
                hist = ticker.history(period="5d")
                if len(hist) >= 2:
                    current = hist["Close"].iloc[-1]
                    prev = hist["Close"].iloc[-2]
                    change_pct = ((current - prev) / prev) * 100
                    changes.append({
                        "symbol": symbol,
                        "price": round(current, 2),
                        "change_pct": round(change_pct, 2),
                    })
            except Exception:
                continue

        # Sort by change percentage
        changes.sort(key=lambda x: x["change_pct"], reverse=True)

        return {
            "top_gainers": changes[:5],
            "top_losers": changes[-5:][::-1],  # Worst first
            "total_advancing": sum(1 for c in changes if c["change_pct"] > 0),
            "total_declining": sum(1 for c in changes if c["change_pct"] < 0),
            "total_unchanged": sum(1 for c in changes if c["change_pct"] == 0),
        }

    def get_sector_performance(self) -> list:
        """
        Get sector-wise performance using sector indices.

        Returns:
            List of sector performance dictionaries
        """
        sectors = {
            "IT": "^CNXIT",
            "Bank": "^NSEBANK",
            "Pharma": "^CNXPHARMA",
            "Auto": "^CNXAUTO",
            "FMCG": "^CNXFMCG",
            "Metal": "^CNXMETAL",
            "Realty": "^CNXREALTY",
            "Energy": "^CNXENERGY",
        }

        results = []
        for sector_name, symbol in sectors.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                if len(hist) >= 2:
                    current = hist["Close"].iloc[-1]
                    prev = hist["Close"].iloc[-2]
                    change_pct = ((current - prev) / prev) * 100
                    results.append({
                        "sector": sector_name,
                        "value": round(current, 2),
                        "change_pct": round(change_pct, 2),
                    })
            except Exception:
                results.append({
                    "sector": sector_name,
                    "value": 0,
                    "change_pct": 0,
                })

        results.sort(key=lambda x: x["change_pct"], reverse=True)
        return results

    def get_market_summary(self) -> dict:
        """
        Get complete daily market summary.

        Returns:
            Dictionary with all market overview data
        """
        print("    Fetching market indices...")
        indices = self.get_market_indices()

        print("    Fetching top gainers/losers...")
        gainers_losers = self.get_top_gainers_losers()

        print("    Fetching sector performance...")
        sectors = self.get_sector_performance()

        # Determine market status
        nifty = indices.get("NIFTY_50", {})
        if nifty.get("change_pct", 0) > 0.5:
            market_status = "Bullish"
        elif nifty.get("change_pct", 0) < -0.5:
            market_status = "Bearish"
        else:
            market_status = "Flat"

        return {
            "date": datetime.now().strftime("%d %b %Y"),
            "time": datetime.now().strftime("%I:%M %p"),
            "market_status": market_status,
            "indices": indices,
            "gainers_losers": gainers_losers,
            "sector_performance": sectors,
        }
