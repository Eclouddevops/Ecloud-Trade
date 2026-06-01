"""
Broker Integration Module (HDFC Securities / Generic)
=====================================================
NOTE: This is a TEMPLATE for broker integration.
Actual trading requires:
1. HDFC Securities API subscription
2. OAuth authentication setup
3. API keys configured in .env

This module provides the interface structure.
For paper trading, it simulates orders locally.
"""
import json
import os
from datetime import datetime


class BrokerInterface:
    """
    Generic broker interface.
    Supports paper trading mode and real broker integration.

    For HDFC Securities:
    - Apply for API access at https://www.hdfcsec.com/
    - Configure API keys in .env file
    - Set TRADING_MODE=live in .env for real trading
    """

    def __init__(self):
        self.mode = os.getenv("TRADING_MODE", "paper")  # paper / live
        self.paper_portfolio = self._load_paper_portfolio()
        self.paper_capital = self.paper_portfolio.get("capital", 1000000)
        self.orders = self.paper_portfolio.get("orders", [])
        self.positions = self.paper_portfolio.get("positions", [])

    def get_account_info(self) -> dict:
        """Get account information."""
        if self.mode == "paper":
            total_pnl = sum(p.get("pnl", 0) for p in self.positions)
            return {
                "mode": "PAPER TRADING",
                "capital": self.paper_capital,
                "available_funds": self.paper_capital - sum(
                    p["qty"] * p["avg_price"] for p in self.positions
                ),
                "margin_used": sum(p["qty"] * p["avg_price"] for p in self.positions),
                "total_pnl": round(total_pnl, 2),
                "positions_count": len(self.positions),
                "orders_today": len([o for o in self.orders if o.get("date") == datetime.now().strftime("%Y-%m-%d")]),
            }
        else:
            return {"mode": "LIVE", "status": "API not configured. Set HDFC_API_KEY in .env"}

    def get_positions(self) -> list:
        """Get current positions."""
        return self.positions

    def get_orders(self) -> list:
        """Get order book."""
        return self.orders[-20:]  # Last 20 orders

    def place_order(self, symbol: str, side: str, qty: int,
                    order_type: str = "MARKET", price: float = 0,
                    stop_loss: float = 0, target: float = 0) -> dict:
        """
        Place an order (paper mode).

        Args:
            symbol: Stock symbol
            side: BUY or SELL
            qty: Quantity
            order_type: MARKET / LIMIT / BRACKET
            price: Limit price (for LIMIT orders)
            stop_loss: Stop loss price
            target: Target price
        """
        if self.mode == "paper":
            order = {
                "id": f"ORD{len(self.orders)+1:04d}",
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "type": order_type,
                "price": price,
                "stop_loss": stop_loss,
                "target": target,
                "status": "EXECUTED",
                "time": datetime.now().strftime("%H:%M:%S"),
                "date": datetime.now().strftime("%Y-%m-%d"),
            }
            self.orders.append(order)

            # Update positions
            if side == "BUY":
                existing = next((p for p in self.positions if p["symbol"] == symbol), None)
                if existing:
                    total_cost = existing["qty"] * existing["avg_price"] + qty * price
                    existing["qty"] += qty
                    existing["avg_price"] = round(total_cost / existing["qty"], 2)
                else:
                    self.positions.append({
                        "symbol": symbol, "qty": qty,
                        "avg_price": price, "side": "LONG", "pnl": 0
                    })
            elif side == "SELL":
                existing = next((p for p in self.positions if p["symbol"] == symbol), None)
                if existing:
                    existing["qty"] -= qty
                    if existing["qty"] <= 0:
                        self.positions.remove(existing)

            self._save_paper_portfolio()
            return {"status": "success", "order": order}
        else:
            return {"status": "error", "message": "Live trading not configured"}

    def close_all_positions(self) -> dict:
        """Emergency: Close all positions."""
        closed = len(self.positions)
        self.positions = []
        self._save_paper_portfolio()
        return {"status": "success", "closed": closed}

    def get_risk_settings(self) -> dict:
        """Get risk management settings."""
        return {
            "max_capital_per_trade": 50000,
            "max_daily_loss": 10000,
            "max_open_positions": 5,
            "auto_stop_loss": True,
            "auto_square_off_time": "15:15",
        }

    def _load_paper_portfolio(self) -> dict:
        path = "data/cache/paper_portfolio.json"
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return {"capital": 1000000, "positions": [], "orders": []}

    def _save_paper_portfolio(self):
        path = "data/cache/paper_portfolio.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "capital": self.paper_capital,
            "positions": self.positions,
            "orders": self.orders[-100:],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
