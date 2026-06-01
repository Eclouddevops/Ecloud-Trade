"""
Data Collection Module
Fetches live and historical market data from NSE/BSE via yfinance and web scraping.
"""
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from config.settings import (
    YFINANCE_SUFFIX,
    HISTORICAL_PERIOD,
    INTERVAL,
    NIFTY50_SYMBOL,
)


class MarketDataCollector:
    """Collects market data for Indian stocks from multiple sources."""

    # Index symbols that don't use .NS suffix
    INDEX_SYMBOLS = {
        "NIFTY": "^NSEI",
        "NIFTY50": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
        "FINNIFTY": "^CNXFIN",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            }
        )

    def _resolve_symbol(self, symbol: str) -> str:
        """Resolve a user-facing symbol to a yfinance ticker symbol."""
        upper = symbol.upper()
        if upper in self.INDEX_SYMBOLS:
            return self.INDEX_SYMBOLS[upper]
        return f"{symbol}{YFINANCE_SUFFIX}"

    def get_stock_data(
        self, symbol: str, period: str = HISTORICAL_PERIOD, interval: str = INTERVAL
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a stock or index.

        Args:
            symbol: Stock symbol (e.g., 'RELIANCE') or index (e.g., 'NIFTY', 'SENSEX')
            period: Data period (e.g., '2y', '1y', '6mo')
            interval: Data interval (e.g., '1d', '1h', '5m')

        Returns:
            DataFrame with OHLCV data
        """
        ticker_symbol = self._resolve_symbol(symbol)
        ticker = yf.Ticker(ticker_symbol)

        df = ticker.history(period=period, interval=interval)

        if df.empty:
            raise ValueError(f"No data found for {symbol}. Check if the symbol is valid.")

        df.index = pd.to_datetime(df.index)
        df = df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

        # Keep only relevant columns
        df = df[["open", "high", "low", "close", "volume"]]
        df = df.dropna()

        return df

    def get_current_price(self, symbol: str) -> dict:
        """
        Get current/latest price info for a stock or index.

        Args:
            symbol: Stock symbol (e.g., 'RELIANCE') or index (e.g., 'SENSEX')

        Returns:
            Dictionary with current price details
        """
        ticker_symbol = self._resolve_symbol(symbol)
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        return {
            "symbol": symbol,
            "current_price": info.get("currentPrice", info.get("regularMarketPrice")),
            "previous_close": info.get("previousClose"),
            "open": info.get("open", info.get("regularMarketOpen")),
            "day_high": info.get("dayHigh", info.get("regularMarketDayHigh")),
            "day_low": info.get("dayLow", info.get("regularMarketDayLow")),
            "volume": info.get("volume", info.get("regularMarketVolume")),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }

    def get_nifty50_data(self, period: str = "6mo") -> pd.DataFrame:
        """Fetch NIFTY 50 index data for market trend analysis."""
        ticker = yf.Ticker(NIFTY50_SYMBOL)
        df = ticker.history(period=period)

        if df.empty:
            raise ValueError("Could not fetch NIFTY 50 data.")

        df.index = pd.to_datetime(df.index)
        df = df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        return df[["open", "high", "low", "close", "volume"]]

    def get_sector_performance(self, symbol: str) -> dict:
        """
        Get sector performance context for a stock.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with sector info
        """
        ticker_symbol = self._resolve_symbol(symbol)
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        return {
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "sector_pe": info.get("sectorPE"),
            "industry_pe": info.get("industryPE"),
        }

    def get_multiple_stocks(self, symbols: list, period: str = "1y") -> dict:
        """
        Fetch data for multiple stocks.

        Args:
            symbols: List of stock symbols
            period: Data period

        Returns:
            Dictionary mapping symbol to DataFrame
        """
        data = {}
        for symbol in symbols:
            try:
                data[symbol] = self.get_stock_data(symbol, period=period)
                print(f"✓ Fetched data for {symbol}")
            except Exception as e:
                print(f"✗ Error fetching {symbol}: {e}")
        return data
