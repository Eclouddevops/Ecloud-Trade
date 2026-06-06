"""
server.py — Option Trading Dashboard Backend
FastAPI + WebSocket for real-time data
"""

import asyncio
import json
import math
import os
import random
import socket
import struct
import time
from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="Option Trading Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── MARKET SIMULATION ENGINE ─────────────────────────────────────────────────

INDICES = {
    "NIFTY50": {"spot": 22450, "lot": 50, "step": 50},
    "BANKNIFTY": {"spot": 47800, "lot": 15, "step": 100},
    "FINNIFTY": {"spot": 20900, "lot": 25, "step": 50},
    "SENSEX": {"spot": 73500, "lot": 10, "step": 100},
    "MIDCPNIFTY": {"spot": 10200, "lot": 75, "step": 25},
}

CRYPTO = {
    "BTC": 68000, "ETH": 3400, "SOL": 165, "BNB": 590,
    "AVAX": 38, "ARB": 1.2, "OP": 2.8, "MATIC": 0.85,
}

_state = {sym: {"price": d["spot"], "iv": 0.15 + random.uniform(0, 0.1)}
          for sym, d in INDICES.items()}
_crypto_state = {sym: {"price": p} for sym, p in CRYPTO.items()}


def simulate_price(current: float, volatility: float = 0.0002) -> float:
    """GBM price simulation"""
    return current * (1 + np.random.normal(0, volatility))


def black_scholes_price(S, K, T, r, sigma, opt_type="CE"):
    from scipy.special import ndtr
    if T <= 0:
        return max(0, S - K) if opt_type == "CE" else max(0, K - S)
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        if opt_type == "CE":
            return max(0.05, S * ndtr(d1) - K * math.exp(-r * T) * ndtr(d2))
        else:
            return max(0.05, K * math.exp(-r * T) * ndtr(-d2) - S * ndtr(-d1))
    except Exception:
        return 0.05


def build_option_chain(symbol: str, expiry_days: int = 7):
    info = INDICES.get(symbol, {"spot": 22450, "lot": 50, "step": 50})
    spot = _state.get(symbol, {}).get("price", info["spot"])
    iv = _state.get(symbol, {}).get("iv", 0.18)
    step = info["step"]
    atm = round(spot / step) * step
    T = max(expiry_days / 365, 0.001)
    r = 0.065

    strikes = [atm + i * step for i in range(-8, 9)]
    chain = []
    for K in strikes:
        ce = black_scholes_price(spot, K, T, r, iv, "CE")
        pe = black_scholes_price(spot, K, T, r, iv, "PE")
        moneyness = "ATM" if K == atm else ("ITM" if K < spot else "OTM")
        chain.append({
            "strike": K,
            "moneyness": moneyness,
            "CE_ltp": round(ce, 2),
            "CE_iv": round(iv * 100 + random.uniform(-1, 1), 2),
            "CE_oi": random.randint(100000, 8000000),
            "CE_vol": random.randint(5000, 800000),
            "CE_delta": round(0.5 + (spot - K) / (spot * 0.05), 3),
            "PE_ltp": round(pe, 2),
            "PE_iv": round(iv * 100 + random.uniform(-1, 1), 2),
            "PE_oi": random.randint(100000, 8000000),
            "PE_vol": random.randint(5000, 800000),
            "PE_delta": round(-0.5 + (K - spot) / (spot * 0.05), 3),
        })
    atm_ce = black_scholes_price(spot, atm, T, r, iv, "CE")
    atm_pe = black_scholes_price(spot, atm, T, r, iv, "PE")
    return {
        "symbol": symbol,
        "spot": round(spot, 2),
        "atm": atm,
        "iv": round(iv * 100, 2),
        "expiry_days": expiry_days,
        "chain": chain,
        "signals": generate_signals(spot, atm, iv, atm_ce, atm_pe),
        "timestamp": datetime.now().isoformat(),
    }


def generate_signals(spot, atm, iv, ce_premium, pe_premium):
    """ATM-based entry/exit signal engine"""
    pcr = random.uniform(0.7, 1.8)
    trend = "BULLISH" if pcr < 0.9 else "BEARISH" if pcr > 1.2 else "NEUTRAL"
    sl_pct = 0.30
    tgt_pct = 0.60

    ce_signal = {
        "type": "CE",
        "strike": atm,
        "entry": round(ce_premium, 2),
        "sl": round(ce_premium * (1 - sl_pct), 2),
        "target1": round(ce_premium * (1 + tgt_pct), 2),
        "target2": round(ce_premium * (1 + tgt_pct * 2), 2),
        "rr": f"1:{round(tgt_pct / sl_pct, 1)}",
        "strength": "STRONG" if iv > 0.18 else "MODERATE",
    }
    pe_signal = {
        "type": "PE",
        "strike": atm,
        "entry": round(pe_premium, 2),
        "sl": round(pe_premium * (1 - sl_pct), 2),
        "target1": round(pe_premium * (1 + tgt_pct), 2),
        "target2": round(pe_premium * (1 + tgt_pct * 2), 2),
        "rr": f"1:{round(tgt_pct / sl_pct, 1)}",
        "strength": "STRONG" if iv > 0.18 else "MODERATE",
    }
    return {
        "pcr": round(pcr, 2),
        "trend": trend,
        "recommended": "CE" if trend == "BULLISH" else "PE" if trend == "BEARISH" else "BOTH",
        "ce": ce_signal,
        "pe": pe_signal,
        "vix": round(iv * 100 * math.sqrt(252 / 365), 2),
    }


def generate_ohlcv(symbol: str, tf_minutes: int = 1, bars: int = 200):
    """Generate historical OHLCV bars for charting"""
    info = INDICES.get(symbol, {"spot": 22450})
    price = info.get("spot", 22450)
    bars_data = []
    now = int(time.time())
    t = now - bars * tf_minutes * 60

    for _ in range(bars):
        o = price
        h = o * (1 + abs(np.random.normal(0, 0.003)))
        l = o * (1 - abs(np.random.normal(0, 0.003)))
        c = o + np.random.normal(0, o * 0.002)
        c = max(l, min(h, c))
        vol = random.randint(50000, 5000000)
        bars_data.append({"time": t, "open": round(o, 2), "high": round(h, 2),
                          "low": round(l, 2), "close": round(c, 2), "volume": vol})
        price = c
        t += tf_minutes * 60

    # Update live state
    if symbol in _state:
        _state[symbol]["price"] = price
    return bars_data


# ─── API ROUTES ───────────────────────────────────────────────────────────────

@app.get("/api/symbols")
async def get_symbols():
    return {"indices": list(INDICES.keys()), "crypto": list(CRYPTO.keys())}


@app.get("/api/option-chain/{symbol}")
async def option_chain(symbol: str, expiry: int = 7):
    return build_option_chain(symbol.upper(), expiry)


@app.get("/api/ohlcv/{symbol}")
async def ohlcv(symbol: str, tf: int = 1, bars: int = 200):
    data = generate_ohlcv(symbol.upper(), tf, bars)
    return {"symbol": symbol, "timeframe": tf, "data": data}


@app.get("/api/market-overview")
async def market_overview():
    overview = []
    for sym, info in INDICES.items():
        price = _state[sym]["price"]
        chg = (price - info["spot"]) / info["spot"] * 100
        overview.append({
            "symbol": sym, "price": round(price, 2),
            "change": round(chg, 2), "iv": round(_state[sym]["iv"] * 100, 2),
        })
    return overview


def get_ntp_time(hosts=None):
    hosts = hosts or ["pool.ntp.org", "time.google.com", "time.cloudflare.com"]
    for host in hosts:
        try:
            msg = b"\x1b" + 47 * b"\0"
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(3)
                sock.sendto(msg, (host, 123))
                data, _ = sock.recvfrom(1024)
            if len(data) < 48:
                continue
            secs = struct.unpack("!12I", data)[10] - 2208988800
            return datetime.utcfromtimestamp(secs)
        except Exception:
            continue
    raise OSError("Failed to sync NTP time")


@app.get("/api/time")
async def api_time():
    source = "server"
    now = datetime.utcnow()
    try:
        now = get_ntp_time()
        source = "ntp"
    except Exception:
        source = "server"

    ist = now + timedelta(hours=5, minutes=30)
    return {
        "utc": now.replace(microsecond=0).isoformat() + "Z",
        "ist": ist.replace(microsecond=0).isoformat(),
        "date": ist.date().isoformat(),
        "time": ist.strftime("%H:%M:%S"),
        "source": source,
        "note": "NTP-synced" if source == "ntp" else "server time fallback",
    }


@app.get("/time")
async def time_alias():
    return await api_time()


@app.get("/api/cloudwatch-logs/{account}")
async def cloudwatch_logs(account: str):
    """Simulated CloudWatch-style logs per account"""
    levels = ["INFO", "INFO", "INFO", "WARN", "ERROR"]
    messages = [
        "Order placed: NIFTY 22450 CE @ 145.00",
        "Position opened: BUY 1 lot BANKNIFTY 48000 PE",
        "Stop-loss triggered: NIFTY 22400 CE exit @ 98.50",
        "Target 1 hit: PE position +52% gain",
        "IV spike detected: VIX moved +2.3 points",
        "PCR crossed 1.2 — bearish signal activated",
        "ATM strike recalculated: 22450 → 22500",
        "WebSocket reconnected successfully",
        "Greeks recalculated for expiry D-3",
        "Risk limit check passed — margin adequate",
    ]
    logs = []
    for i in range(20):
        ts = datetime.now() - timedelta(minutes=i * 2)
        logs.append({
            "timestamp": ts.strftime("%H:%M:%S"),
            "level": random.choice(levels),
            "account": account,
            "message": random.choice(messages),
        })
    return logs


# ─── WEBSOCKET ────────────────────────────────────────────────────────────────

active_connections: List[WebSocket] = []


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Simulate price ticks
            for sym in _state:
                _state[sym]["price"] = simulate_price(_state[sym]["price"])
                _state[sym]["iv"] = max(0.10, min(0.50, _state[sym]["iv"] + np.random.normal(0, 0.001)))

            payload = {
                "type": "tick",
                "data": {
                    sym: {
                        "price": round(_state[sym]["price"], 2),
                        "iv": round(_state[sym]["iv"] * 100, 2),
                        "change": round(random.uniform(-0.5, 0.5), 2),
                    }
                    for sym in _state
                },
                "crypto": {
                    sym: round(simulate_price(_crypto_state[sym]["price"], 0.001), 4)
                    for sym in _crypto_state
                },
                "ts": datetime.now().isoformat(),
            }
            await websocket.send_json(payload)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        active_connections.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
