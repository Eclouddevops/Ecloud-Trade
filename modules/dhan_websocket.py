"""
Dhan WebSocket Live Market Data Streamer
Streams real-time NIFTY 50, BANKNIFTY, SENSEX tick-by-tick.
Includes auto-reconnect, error handling, and logging.

Requirements:
    pip install dhanhq
    .env must have DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN

Usage:
    from modules.dhan_websocket import DhanWebSocketFeed
    feed = DhanWebSocketFeed()
    feed.start()  # Starts streaming in background thread
    feed.get_latest()  # Returns latest prices
"""
import os
import time
import json
import logging
import threading
from datetime import datetime
from collections import defaultdict

# Setup logging
logging.basicConfig(
    filename='data/cache/websocket.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S+05:30'
)
logger = logging.getLogger('DhanWS')


# Dhan security IDs for indices
DHAN_INSTRUMENTS = {
    "NIFTY": {"security_id": "13", "exchange": "IDX_I", "name": "NIFTY 50"},
    "BANKNIFTY": {"security_id": "25", "exchange": "IDX_I", "name": "NIFTY BANK"},
    "SENSEX": {"security_id": "1", "exchange": "BSE_IDX", "name": "SENSEX"},
}


class DhanWebSocketFeed:
    """
    Real-time market data feed via Dhan WebSocket.
    Auto-reconnects on failure with exponential backoff.
    """

    def __init__(self):
        self.client_id = os.getenv("DHAN_CLIENT_ID", "")
        self.access_token = os.getenv("DHAN_ACCESS_TOKEN", "")
        self.is_configured = bool(self.client_id and self.access_token)
        self.is_running = False
        self.is_connected = False
        self._thread = None
        self._reconnect_count = 0
        self._max_reconnects = 50
        self._latest_data = {}
        self._lock = threading.Lock()
        self._callbacks = []
        self._last_update = None

    def start(self):
        """Start WebSocket feed in background thread."""
        if not self.is_configured:
            logger.warning("Dhan credentials not configured. Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in .env")
            return False

        if self.is_running:
            return True

        self.is_running = True
        self._thread = threading.Thread(target=self._run_feed, daemon=True)
        self._thread.start()
        logger.info("Dhan WebSocket feed started")
        return True

    def stop(self):
        """Stop the feed."""
        self.is_running = False
        self.is_connected = False
        logger.info("Dhan WebSocket feed stopped")

    def get_latest(self) -> dict:
        """Get latest prices for all instruments."""
        with self._lock:
            result = dict(self._latest_data)
        result["connected"] = self.is_connected
        result["source"] = "Dhan WebSocket" if self.is_connected else "Dhan REST"
        result["last_update"] = self._last_update
        result["reconnect_count"] = self._reconnect_count
        return result

    def on_tick(self, callback):
        """Register callback for tick updates: callback(data)"""
        self._callbacks.append(callback)

    def _run_feed(self):
        """Main feed loop with auto-reconnect."""
        while self.is_running:
            try:
                self._connect_and_stream()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.is_connected = False

            if not self.is_running:
                break

            # Exponential backoff for reconnect
            self._reconnect_count += 1
            if self._reconnect_count > self._max_reconnects:
                logger.error("Max reconnects reached. Stopping feed.")
                self.is_running = False
                break

            wait_time = min(30, 2 ** min(self._reconnect_count, 5))
            logger.info(f"Reconnecting in {wait_time}s (attempt {self._reconnect_count})")
            time.sleep(wait_time)

    def _connect_and_stream(self):
        """Connect to Dhan and stream data. Falls back to REST polling if WS fails."""
        try:
            from dhanhq import marketfeed

            instruments = []
            for name, info in DHAN_INSTRUMENTS.items():
                instruments.append((
                    int(marketfeed.IDX) if "IDX" in info["exchange"] else int(marketfeed.BSE),
                    info["security_id"],
                    int(marketfeed.Ticker)
                ))

            feed = marketfeed.DhanFeed(
                self.client_id,
                self.access_token,
                instruments
            )

            self.is_connected = True
            self._reconnect_count = 0
            logger.info("Dhan WebSocket connected successfully")

            def on_data(data):
                self._process_tick(data)

            feed.on_ticks = on_data
            feed.connect()

            # Keep alive
            while self.is_running and self.is_connected:
                time.sleep(1)

            feed.close()

        except ImportError:
            logger.warning("dhanhq not installed. Using REST polling fallback.")
            self._poll_rest()
        except Exception as e:
            logger.error(f"Dhan WS connection failed: {e}. Using REST fallback.")
            self._poll_rest()

    def _poll_rest(self):
        """Fallback: Poll Dhan REST API every 2 seconds."""
        try:
            from dhanhq import dhanhq
            dhan = dhanhq(self.client_id, self.access_token)

            logger.info("Using Dhan REST polling (2s interval)")
            self.is_connected = True

            while self.is_running:
                for name, info in DHAN_INSTRUMENTS.items():
                    try:
                        # Use market quote
                        seg = "IDX_I" if "IDX" in info["exchange"] else "BSE"
                        quote = dhan.intraday_daily_minute_charts(
                            security_id=info["security_id"],
                            exchange_segment=seg,
                            instrument_type="INDEX"
                        )
                        if quote and "data" in quote:
                            close_prices = quote["data"].get("close", [])
                            if close_prices:
                                price = close_prices[-1]
                                self._update_price(name, price)
                    except Exception:
                        pass
                time.sleep(2)

        except ImportError:
            logger.error("dhanhq package not installed. Run: pip install dhanhq")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Dhan REST polling failed: {e}")
            self.is_connected = False

    def _process_tick(self, data):
        """Process incoming tick data from WebSocket."""
        try:
            security_id = str(data.get("security_id", ""))
            ltp = data.get("LTP", data.get("ltp", 0))

            for name, info in DHAN_INSTRUMENTS.items():
                if info["security_id"] == security_id:
                    self._update_price(name, ltp)
                    break
        except Exception as e:
            logger.error(f"Tick processing error: {e}")

    def _update_price(self, name, price):
        """Update latest price and notify callbacks."""
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:30")
        with self._lock:
            prev = self._latest_data.get(name, {}).get("price", price)
            change = price - prev if prev else 0
            self._latest_data[name] = {
                "price": round(price, 2),
                "change": round(change, 2),
                "timestamp": now,
                "source": "Dhan WebSocket",
            }
        self._last_update = now

        # Notify callbacks
        for cb in self._callbacks:
            try:
                cb(self._latest_data)
            except Exception:
                pass

    def get_status(self) -> dict:
        """Get connection status."""
        return {
            "configured": self.is_configured,
            "connected": self.is_connected,
            "running": self.is_running,
            "reconnects": self._reconnect_count,
            "last_update": self._last_update,
            "source": "Dhan WebSocket" if self.is_connected else "Disconnected",
        }
