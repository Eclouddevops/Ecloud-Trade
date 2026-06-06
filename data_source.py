"""
data_source.py — Pluggable data source for Option Trading Dashboard
Swap brokers by adding/modifying a single function below.
Supported: yfinance (Indian stocks), Hyperliquid (crypto), Zerodha (future), Alpaca (future)
"""

import asyncio
import json
import math
import random
import time
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

# ─── DATA SOURCE REGISTRY ─────────────────────────────────────────────────────
# Add your broker function here and register it in SOURCES dict

def get_yfinance_data(symbol: str, interval: str = "1m", period: str = "1d"):
    """Indian stocks / NSE options via yfinance"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            return None
        return {
            "source": "yfinance",
            "symbol": symbol,
            "ohlcv": [
                {
                    "time": int(row.Index.timestamp()),
                    "open": round(row.Open, 2),
                    "high": round(row.High, 2),
                    "low": round(row.Low, 2),
                    "close": round(row.Close, 2),
                    "volume": int(row.Volume),
                }
                for row in hist.itertuples()
            ],
        }
    except Exception as e:
        return {"error": str(e)}


def get_hyperliquid_data(symbol: str):
    """Crypto prices via Hyperliquid WebSocket (stub — connect via WS in frontend)"""
    return {"source": "hyperliquid", "symbol": symbol, "note": "Connect via WS"}


def get_zerodha_data(symbol: str, api_key: str = None):
    """Zerodha Kite Connect — add your API key"""
    # from kiteconnect import KiteConnect
    # kite = KiteConnect(api_key=api_key)
    return {"source": "zerodha", "symbol": symbol, "note": "Add Kite credentials"}


def get_alpaca_data(symbol: str):
    """Alpaca Markets — US stocks"""
    # from alpaca_trade_api import REST
    return {"source": "alpaca", "symbol": symbol, "note": "Add Alpaca credentials"}


def get_binance_data(symbol: str):
    """Binance crypto"""
    return {"source": "binance", "symbol": symbol, "note": "Add Binance credentials"}


# ─── SOURCE REGISTRY ──────────────────────────────────────────────────────────
SOURCES = {
    "yfinance": get_yfinance_data,
    "hyperliquid": get_hyperliquid_data,
    "zerodha": get_zerodha_data,
    "alpaca": get_alpaca_data,
    "binance": get_binance_data,
}


def fetch(source: str, symbol: str, **kwargs):
    """Universal fetch entry point"""
    fn = SOURCES.get(source)
    if not fn:
        return {"error": f"Unknown source: {source}. Available: {list(SOURCES.keys())}"}
    return fn(symbol, **kwargs)


# ─── OPTION CHAIN CALCULATOR ──────────────────────────────────────────────────

def black_scholes(S, K, T, r, sigma, option_type="CE"):
    """Black-Scholes pricing for CE/PE"""
    if T <= 0:
        return max(0, S - K) if option_type == "CE" else max(0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    from scipy.stats import norm
    if option_type == "CE":
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return round(price, 2)


def calculate_greeks(S, K, T, r, sigma, option_type="CE"):
    """Delta, Gamma, Theta, Vega, Rho"""
    try:
        from scipy.stats import norm
        if T <= 0:
            return {"delta": 1.0 if option_type == "CE" else -1.0, "gamma": 0, "theta": 0, "vega": 0}
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        delta = norm.cdf(d1) if option_type == "CE" else norm.cdf(d1) - 1
        gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
        theta = (-(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T)) -
                 r * K * math.exp(-r * T) * (norm.cdf(d2) if option_type == "CE" else norm.cdf(-d2))) / 365
        vega = S * norm.pdf(d1) * math.sqrt(T) / 100
        return {
            "delta": round(delta, 4),
            "gamma": round(gamma, 6),
            "theta": round(theta, 2),
            "vega": round(vega, 4),
        }
    except Exception:
        return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}


def generate_option_chain(spot: float, expiry_days: int = 7, iv: float = 0.18):
    """Generate full option chain with CE/PE for ATM ±10 strikes"""
    r = 0.065  # Risk-free rate (RBI repo)
    T = expiry_days / 365
    step = 50 if spot > 20000 else 100 if spot > 10000 else 50
    atm = round(spot / step) * step
    strikes = [atm + (i * step) for i in range(-10, 11)]

    chain = []
    for K in strikes:
        ce_price = black_scholes(spot, K, T, r, iv, "CE")
        pe_price = black_scholes(spot, K, T, r, iv, "PE")
        ce_greeks = calculate_greeks(spot, K, T, r, iv, "CE")
        pe_greeks = calculate_greeks(spot, K, T, r, iv, "PE")
        moneyness = "ATM" if K == atm else ("ITM" if K < atm else "OTM")
        chain.append({
            "strike": K,
            "moneyness": moneyness,
            "CE": {
                "ltp": ce_price,
                "iv": round(iv * 100, 2),
                "oi": random.randint(50000, 5000000),
                "volume": random.randint(1000, 500000),
                **ce_greeks,
            },
            "PE": {
                "ltp": pe_price,
                "iv": round(iv * 100, 2),
                "oi": random.randint(50000, 5000000),
                "volume": random.randint(1000, 500000),
                **pe_greeks,
            },
        })
    return chain


def get_entry_exit_levels(spot: float, option_type: str, strike: float, premium: float):
    """Calculate entry, stop-loss, target levels"""
    sl_pct = 0.30   # 30% stop-loss on premium
    tgt1_pct = 0.50  # 50% target 1
    tgt2_pct = 1.0   # 100% target 2 (double)
    return {
        "entry": round(premium, 2),
        "stop_loss": round(premium * (1 - sl_pct), 2),
        "target_1": round(premium * (1 + tgt1_pct), 2),
        "target_2": round(premium * (1 + tgt2_pct), 2),
        "spot_entry": round(spot, 2),
        "spot_sl": round(spot * (0.99 if option_type == "CE" else 1.01), 2),
        "spot_tgt1": round(spot * (1.005 if option_type == "CE" else 0.995), 2),
        "risk_reward": f"1:{round(tgt1_pct / sl_pct, 1)}",
    }
