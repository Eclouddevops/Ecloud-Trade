"""
Global Market Monitor Module
Tracks international indices, commodities, and currencies.
"""
import yfinance as yf


class GlobalMarketMonitor:
    """Monitors global markets, commodities, and forex."""

    INDICES = {
        "NIFTY_50": "^NSEI",
        "SENSEX": "^BSESN",
        "BANK_NIFTY": "^NSEBANK",
        "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
        "DOW_JONES": "^DJI",
        "NASDAQ": "^IXIC",
        "SP500": "^GSPC",
        "FTSE": "^FTSE",
        "NIKKEI": "^N225",
        "HANG_SENG": "^HSI",
    }

    COMMODITIES = {
        "GOLD": "GC=F",
        "SILVER": "SI=F",
        "CRUDE_OIL": "CL=F",
        "NATURAL_GAS": "NG=F",
    }

    FOREX = {
        "USD_INR": "USDINR=X",
        "EUR_INR": "EURINR=X",
        "GBP_INR": "GBPINR=X",
        "DXY": "DX-Y.NYB",
    }

    def get_global_indices(self) -> dict:
        """Fetch all global index data."""
        return self._fetch_batch(self.INDICES)

    def get_commodities(self) -> dict:
        """Fetch commodity prices."""
        return self._fetch_batch(self.COMMODITIES)

    def get_forex(self) -> dict:
        """Fetch forex rates."""
        return self._fetch_batch(self.FOREX)

    def get_all(self) -> dict:
        """Get complete global market snapshot."""
        return {
            "indices": self.get_global_indices(),
            "commodities": self.get_commodities(),
            "forex": self.get_forex(),
        }

    def _fetch_batch(self, symbols: dict) -> dict:
        result = {}
        for name, symbol in symbols.items():
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
                    result[name] = {"value": round(hist["Close"].iloc[-1], 2), "change": 0, "change_pct": 0}
            except Exception:
                result[name] = {"value": 0, "change": 0, "change_pct": 0}
        return result
