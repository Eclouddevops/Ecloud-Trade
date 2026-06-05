"""
NSE India Live Data Fetcher
Fetches real-time index prices directly from NSE India's public API.
No API key required. Free. Near real-time during market hours.

Endpoints used:
- https://www.nseindia.com/api/allIndices (all index data)
- https://www.nseindia.com/api/marketStatus (market open/close)
"""
import requests
import time
from datetime import datetime


class NSELiveData:
    """Fetches real-time data from NSE India's public website API."""

    BASE_URL = "https://www.nseindia.com"
    INDICES_URL = "https://www.nseindia.com/api/allIndices"
    MARKET_STATUS_URL = "https://www.nseindia.com/api/marketStatus"

    # Map our names to NSE index names
    INDEX_MAP = {
        "NIFTY": "NIFTY 50",
        "NIFTY50": "NIFTY 50",
        "BANKNIFTY": "NIFTY BANK",
        "SENSEX": "SENSEX",  # BSE - may not be in NSE API
        "FINNIFTY": "NIFTY FINANCIAL SERVICES",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _set_cookies(self):
        """No-op — NSE API works without cookies from this machine."""
        pass

    def get_all_indices(self) -> dict:
        """
        Fetch all index data from NSE.
        Returns dict with NIFTY, BANKNIFTY prices and changes.
        """
        self._set_cookies()
        try:
            r = self.session.get(self.INDICES_URL, timeout=10)
            if r.status_code != 200:
                return {"error": f"NSE returned status {r.status_code}"}

            data = r.json()
            indices = data.get("data", [])

            result = {}
            for idx in indices:
                name = idx.get("index", "")
                # Match to our names
                for our_name, nse_name in self.INDEX_MAP.items():
                    if name == nse_name:
                        result[our_name] = {
                            "price": round(idx.get("last", 0), 2),
                            "change": round(idx.get("variation", 0), 2),
                            "change_pct": round(idx.get("percentChange", 0), 2),
                            "prev_close": round(idx.get("previousClose", 0), 2),
                            "open": round(idx.get("open", 0), 2),
                            "high": round(idx.get("high", 0), 2),
                            "low": round(idx.get("low", 0), 2),
                            "source": "NSE India (Live)",
                        }
                        break

            return result
        except requests.exceptions.Timeout:
            return {"error": "NSE API timeout"}
        except Exception as e:
            return {"error": str(e)}

    def get_live_prices(self) -> dict:
        """
        Get live prices for NIFTY, BANKNIFTY, SENSEX.
        Primary method called by the dashboard every 5 seconds.
        """
        result = self.get_all_indices()

        if "error" in result:
            return result

        # Add SENSEX via BSE if not in NSE data
        if "SENSEX" not in result:
            sensex = self._fetch_sensex()
            if sensex:
                result["SENSEX"] = sensex

        # Add timestamp and market status
        now = datetime.now()
        current_min = now.hour * 60 + now.minute
        is_market = 9*60+15 <= current_min <= 15*60+30
        weekday = now.weekday()

        result["timestamp"] = now.isoformat()
        result["market_status"] = "Open" if (is_market and weekday < 5) else "Closed"
        result["broker"] = "NSE India (Live)"

        return result

    def _fetch_sensex(self) -> dict:
        """Fetch SENSEX from BSE API."""
        try:
            url = "https://api.bseindia.com/BseIndiaAPI/api/Sensex/getSensexData?json=t"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bseindia.com/",
                "Accept": "application/json",
            }
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if data and len(data) > 0:
                    sensex = data[0] if isinstance(data, list) else data
                    ltp = float(sensex.get("ltp", sensex.get("currentValue", 0)))
                    change = float(sensex.get("change", sensex.get("chg", 0)))
                    prev = ltp - change if change else ltp
                    change_pct = (change / prev * 100) if prev else 0
                    return {
                        "price": round(ltp, 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                        "prev_close": round(prev, 2),
                        "high": round(float(sensex.get("high", ltp)), 2),
                        "low": round(float(sensex.get("low", ltp)), 2),
                        "source": "BSE India (Live)",
                    }
        except Exception:
            pass

        # Fallback: use Yahoo for SENSEX only
        try:
            import yfinance as yf
            ticker = yf.Ticker("^BSESN")
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                current = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                return {
                    "price": round(current, 2),
                    "change": round(current - prev, 2),
                    "change_pct": round((current - prev) / prev * 100, 2),
                    "prev_close": round(prev, 2),
                    "high": round(float(hist["High"].iloc[-1]), 2),
                    "low": round(float(hist["Low"].iloc[-1]), 2),
                    "source": "Yahoo (SENSEX fallback)",
                }
        except Exception:
            return None

    def get_market_status(self) -> dict:
        """Check if market is open/closed."""
        self._set_cookies()
        try:
            r = self.session.get(self.MARKET_STATUS_URL, timeout=10)
            if r.status_code == 200:
                data = r.json()
                status = data.get("marketState", [])
                for s in status:
                    if s.get("market") == "Capital Market":
                        return {
                            "status": s.get("marketStatus", "Unknown"),
                            "message": s.get("tradeDate", ""),
                        }
            return {"status": "Unknown"}
        except Exception:
            return {"status": "Unknown"}
