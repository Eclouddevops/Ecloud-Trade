"""
Broker Adapters for Real-Time Market Data
Supports: Zerodha Kite, Angel One (SmartAPI), Dhan
Falls back to Yahoo Finance if no broker is configured.

Setup:
1. Add your broker API keys to .env file
2. The system auto-detects which broker is configured
3. Real-time WebSocket streaming during market hours

Required packages (install the one you need):
- Zerodha: pip install kiteconnect
- Angel One: pip install smartapi-python
- Dhan: pip install dhanhq
"""
import os
from datetime import datetime
from abc import ABC, abstractmethod


class BrokerAdapter(ABC):
    """Base class for broker adapters."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if this broker's API keys are set."""
        pass

    @abstractmethod
    def get_live_price(self, symbol: str) -> dict:
        """Get real-time price for a symbol."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get broker name."""
        pass


class ZerodhaAdapter(BrokerAdapter):
    """
    Zerodha Kite Connect adapter for real-time data.

    Required .env variables:
        ZERODHA_API_KEY=your_api_key
        ZERODHA_API_SECRET=your_api_secret
        ZERODHA_ACCESS_TOKEN=your_access_token
    """

    SYMBOL_MAP = {
        "NIFTY": "NSE:NIFTY 50",
        "BANKNIFTY": "NSE:NIFTY BANK",
        "SENSEX": "BSE:SENSEX",
    }

    def __init__(self):
        self.api_key = os.getenv("ZERODHA_API_KEY", "")
        self.api_secret = os.getenv("ZERODHA_API_SECRET", "")
        self.access_token = os.getenv("ZERODHA_ACCESS_TOKEN", "")
        self.kite = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.access_token)

    def get_name(self) -> str:
        return "Zerodha Kite"

    def _connect(self):
        if self.kite is None:
            try:
                from kiteconnect import KiteConnect
                self.kite = KiteConnect(api_key=self.api_key)
                self.kite.set_access_token(self.access_token)
            except ImportError:
                raise ImportError("Install kiteconnect: pip install kiteconnect")

    def get_live_price(self, symbol: str) -> dict:
        self._connect()
        trading_symbol = self.SYMBOL_MAP.get(symbol.upper(), f"NSE:{symbol}")
        try:
            quote = self.kite.quote([trading_symbol])
            data = quote[trading_symbol]
            return {
                "price": round(data["last_price"], 2),
                "change": round(data["net_change"], 2),
                "change_pct": round(data["net_change"] / data["ohlc"]["close"] * 100, 2) if data["ohlc"]["close"] else 0,
                "prev_close": round(data["ohlc"]["close"], 2),
                "high": round(data["ohlc"]["high"], 2),
                "low": round(data["ohlc"]["low"], 2),
                "open": round(data["ohlc"]["open"], 2),
                "volume": data.get("volume", 0),
                "source": "Zerodha Kite (Real-time)",
            }
        except Exception as e:
            return {"error": str(e)}


class AngelOneAdapter(BrokerAdapter):
    """
    Angel One SmartAPI adapter for real-time data.

    Required .env variables:
        ANGEL_API_KEY=your_api_key
        ANGEL_CLIENT_ID=your_client_id
        ANGEL_PASSWORD=your_password
        ANGEL_TOTP_SECRET=your_totp_secret
    """

    SYMBOL_MAP = {
        "NIFTY": {"exchange": "NSE", "tradingsymbol": "Nifty 50", "symboltoken": "99926000"},
        "BANKNIFTY": {"exchange": "NSE", "tradingsymbol": "Nifty Bank", "symboltoken": "99926009"},
        "SENSEX": {"exchange": "BSE", "tradingsymbol": "SENSEX", "symboltoken": "99919000"},
    }

    def __init__(self):
        self.api_key = os.getenv("ANGEL_API_KEY", "")
        self.client_id = os.getenv("ANGEL_CLIENT_ID", "")
        self.password = os.getenv("ANGEL_PASSWORD", "")
        self.totp_secret = os.getenv("ANGEL_TOTP_SECRET", "")
        self.smart_api = None

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client_id and self.password)

    def get_name(self) -> str:
        return "Angel One"

    def _connect(self):
        if self.smart_api is None:
            try:
                from SmartApi import SmartConnect
                import pyotp
                self.smart_api = SmartConnect(api_key=self.api_key)
                totp = pyotp.TOTP(self.totp_secret).now() if self.totp_secret else ""
                self.smart_api.generateSession(self.client_id, self.password, totp)
            except ImportError:
                raise ImportError("Install SmartAPI: pip install smartapi-python pyotp")

    def get_live_price(self, symbol: str) -> dict:
        self._connect()
        sym_info = self.SYMBOL_MAP.get(symbol.upper())
        if not sym_info:
            return {"error": f"Symbol {symbol} not mapped for Angel One"}
        try:
            data = self.smart_api.ltpData(sym_info["exchange"], sym_info["tradingsymbol"], sym_info["symboltoken"])
            ltp = data["data"]["ltp"]
            return {
                "price": round(ltp, 2),
                "change": 0,
                "change_pct": 0,
                "prev_close": 0,
                "high": 0,
                "low": 0,
                "source": "Angel One (Real-time)",
            }
        except Exception as e:
            return {"error": str(e)}


class DhanAdapter(BrokerAdapter):
    """
    Dhan API adapter for real-time data.

    Required .env variables:
        DHAN_CLIENT_ID=your_client_id
        DHAN_ACCESS_TOKEN=your_access_token
    """

    SYMBOL_MAP = {
        "NIFTY": {"security_id": "13", "exchange": "NSE"},
        "BANKNIFTY": {"security_id": "25", "exchange": "NSE"},
        "SENSEX": {"security_id": "1", "exchange": "BSE"},
    }

    def __init__(self):
        self.client_id = os.getenv("DHAN_CLIENT_ID", "")
        self.access_token = os.getenv("DHAN_ACCESS_TOKEN", "")
        self.dhan = None

    def is_configured(self) -> bool:
        return bool(self.client_id and self.access_token)

    def get_name(self) -> str:
        return "Dhan"

    def _connect(self):
        if self.dhan is None:
            try:
                from dhanhq import dhanhq
                self.dhan = dhanhq(self.client_id, self.access_token)
            except ImportError:
                raise ImportError("Install Dhan: pip install dhanhq")

    def get_live_price(self, symbol: str) -> dict:
        self._connect()
        sym_info = self.SYMBOL_MAP.get(symbol.upper())
        if not sym_info:
            return {"error": f"Symbol {symbol} not mapped for Dhan"}
        try:
            data = self.dhan.get_market_quote(
                security_id=sym_info["security_id"],
                exchange_segment=sym_info["exchange"]
            )
            if data and "data" in data:
                quote = data["data"]
                return {
                    "price": round(quote.get("LTP", 0), 2),
                    "change": round(quote.get("change", 0), 2),
                    "change_pct": round(quote.get("changePer", 0), 2),
                    "prev_close": round(quote.get("prevClose", 0), 2),
                    "high": round(quote.get("high", 0), 2),
                    "low": round(quote.get("low", 0), 2),
                    "source": "Dhan (Real-time)",
                }
            return {"error": "No data from Dhan"}
        except Exception as e:
            return {"error": str(e)}


class YahooFinanceAdapter(BrokerAdapter):
    """Fallback adapter using Yahoo Finance (15-min delayed)."""

    SYMBOL_MAP = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
    }

    def is_configured(self) -> bool:
        return True  # Always available

    def get_name(self) -> str:
        return "Yahoo Finance (Delayed)"

    def get_live_price(self, symbol: str) -> dict:
        import yfinance as yf
        yf_symbol = self.SYMBOL_MAP.get(symbol.upper(), f"{symbol}.NS")
        try:
            ticker = yf.Ticker(yf_symbol)
            # Try 1-min data first
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty:
                current = float(hist["Close"].iloc[-1])
                open_price = float(hist["Open"].iloc[0])
                day_high = float(hist["High"].max())
                day_low = float(hist["Low"].min())
                change = current - open_price
                change_pct = (change / open_price) * 100 if open_price else 0
                return {
                    "price": round(current, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "prev_close": round(open_price, 2),
                    "high": round(day_high, 2),
                    "low": round(day_low, 2),
                    "source": "Yahoo Finance (15-min delay)",
                }
            # Fallback to daily
            hist = ticker.history(period="5d", interval="1d")
            if len(hist) >= 2:
                current = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                change = current - prev
                change_pct = (change / prev) * 100
                return {
                    "price": round(current, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "prev_close": round(prev, 2),
                    "high": round(float(hist["High"].iloc[-1]), 2),
                    "low": round(float(hist["Low"].iloc[-1]), 2),
                    "source": "Yahoo Finance (Daily)",
                }
            return {"error": "No data available"}
        except Exception as e:
            return {"error": str(e)}


class BrokerManager:
    """
    Manages broker connections. Tries configured brokers in priority order,
    falls back to Yahoo Finance.

    Priority: Zerodha > Angel One > Dhan > Yahoo Finance
    """

    def __init__(self):
        self.adapters = [
            ZerodhaAdapter(),
            AngelOneAdapter(),
            DhanAdapter(),
            YahooFinanceAdapter(),
        ]
        self._active_adapter = None

    def get_active_broker(self) -> BrokerAdapter:
        """Get the first configured broker adapter."""
        if self._active_adapter is None:
            for adapter in self.adapters:
                if adapter.is_configured():
                    self._active_adapter = adapter
                    break
        return self._active_adapter

    def get_live_prices(self) -> dict:
        """Get live prices for all indices using the best available broker."""
        adapter = self.get_active_broker()
        indices = ["NIFTY", "BANKNIFTY", "SENSEX"]
        result = {}

        for idx in indices:
            data = adapter.get_live_price(idx)
            if "error" not in data:
                result[idx] = data
            else:
                # Try Yahoo as fallback
                yahoo = YahooFinanceAdapter()
                result[idx] = yahoo.get_live_price(idx)

        result["broker"] = adapter.get_name()
        result["timestamp"] = datetime.now().isoformat()

        # Market hours check
        now = datetime.now()
        current_min = now.hour * 60 + now.minute
        is_market = 9*60+15 <= current_min <= 15*60+30
        weekday = now.weekday()
        result["market_status"] = "Open" if (is_market and weekday < 5) else "Closed"

        return result

    def get_status(self) -> dict:
        """Get broker connection status."""
        statuses = []
        for adapter in self.adapters:
            statuses.append({
                "name": adapter.get_name(),
                "configured": adapter.is_configured(),
                "active": adapter == self._active_adapter,
            })
        return {"brokers": statuses, "active": self.get_active_broker().get_name()}
