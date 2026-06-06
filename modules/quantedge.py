"""
QuantEdge Option Trading Engine
Black-Scholes ATM-based signals with SL, T1, T2 levels.
PCR-based strategy recommendations (Bull/Bear/Straddle).
Supports NIFTY50, BANKNIFTY, FINNIFTY, SENSEX, MIDCPNIFTY.

Signal Logic:
- ATM Strike = round(Spot / Step) * Step
- CE Entry = ATM CE estimated premium
- PE Entry = ATM PE estimated premium
- Stop Loss = Entry x 0.70 (-30%)
- Target 1 = Entry x 1.50 (+50%)
- Target 2 = Entry x 2.00 (+100%)
- Risk:Reward = 1:1.67
- PCR < 0.9 → BULLISH → Recommend CE
- PCR > 1.2 → BEARISH → Recommend PE
- PCR 0.9–1.2 → NEUTRAL → Recommend Straddle
"""
import math
import pandas as pd
import numpy as np
import ta
from datetime import datetime


# Symbol configuration
SYMBOLS = {
    "NIFTY50": {"lot_size": 50, "strike_step": 50},
    "NIFTY": {"lot_size": 50, "strike_step": 50},
    "BANKNIFTY": {"lot_size": 15, "strike_step": 100},
    "FINNIFTY": {"lot_size": 25, "strike_step": 50},
    "SENSEX": {"lot_size": 10, "strike_step": 100},
    "MIDCPNIFTY": {"lot_size": 75, "strike_step": 25},
}


class QuantEdgeEngine:
    """Option trading signal engine with Black-Scholes pricing."""

    def black_scholes_call(self, S, K, T, r, sigma):
        """Calculate Black-Scholes call option price."""
        if T <= 0 or sigma <= 0:
            return max(0, S - K)
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        from statistics import NormalDist
        nd = NormalDist()
        return S * nd.cdf(d1) - K * math.exp(-r * T) * nd.cdf(d2)

    def black_scholes_put(self, S, K, T, r, sigma):
        """Calculate Black-Scholes put option price."""
        if T <= 0 or sigma <= 0:
            return max(0, K - S)
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        from statistics import NormalDist
        nd = NormalDist()
        return K * math.exp(-r * T) * nd.cdf(-d2) - S * nd.cdf(-d1)

    def calculate_greeks(self, S, K, T, r, sigma, option_type="CE"):
        """Calculate option Greeks (Delta, Gamma, Theta, Vega)."""
        if T <= 0 or sigma <= 0:
            return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}
        from statistics import NormalDist
        nd = NormalDist()
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        gamma = nd.pdf(d1) / (S * sigma * math.sqrt(T))
        vega = S * nd.pdf(d1) * math.sqrt(T) / 100

        if option_type == "CE":
            delta = nd.cdf(d1)
            theta = (-(S * nd.pdf(d1) * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * nd.cdf(d2)) / 365
        else:
            delta = nd.cdf(d1) - 1
            theta = (-(S * nd.pdf(d1) * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * nd.cdf(-d2)) / 365

        return {
            "delta": round(delta, 4),
            "gamma": round(gamma, 6),
            "theta": round(theta, 2),
            "vega": round(vega, 2),
        }

    def generate_signals(self, spot_price: float, symbol: str, df: pd.DataFrame = None) -> dict:
        """
        Generate complete option trading signals.

        Args:
            spot_price: Current spot price
            symbol: Index symbol (NIFTY, BANKNIFTY, etc.)
            df: Optional OHLCV DataFrame for volatility calculation

        Returns:
            Complete signal with entry, SL, targets, Greeks, strategy
        """
        config = SYMBOLS.get(symbol.upper(), SYMBOLS.get("NIFTY"))
        step = config["strike_step"]
        lot_size = config["lot_size"]

        # ATM Strike
        atm = round(spot_price / step) * step

        # Calculate IV from historical data or use default
        if df is not None and len(df) > 20:
            returns = df["close"].pct_change().dropna()
            hv = float(returns.tail(20).std() * math.sqrt(252))
        else:
            hv = 0.15  # Default 15% volatility

        # Time to expiry (assume weekly expiry, ~3 days avg)
        T = 3 / 365
        r = 0.065  # RBI repo rate ~6.5%

        # Black-Scholes pricing
        ce_price = self.black_scholes_call(spot_price, atm, T, r, hv)
        pe_price = self.black_scholes_put(spot_price, atm, T, r, hv)

        # ITM / OTM strikes
        itm_ce = atm - step
        otm_ce = atm + step
        itm_pe = atm + step
        otm_pe = atm - step

        itm_ce_price = self.black_scholes_call(spot_price, itm_ce, T, r, hv)
        otm_ce_price = self.black_scholes_call(spot_price, otm_ce, T, r, hv)
        itm_pe_price = self.black_scholes_put(spot_price, itm_pe, T, r, hv)
        otm_pe_price = self.black_scholes_put(spot_price, otm_pe, T, r, hv)

        # Greeks for ATM
        ce_greeks = self.calculate_greeks(spot_price, atm, T, r, hv, "CE")
        pe_greeks = self.calculate_greeks(spot_price, atm, T, r, hv, "PE")

        # Signal levels
        ce_entry = round(ce_price, 2)
        ce_sl = round(ce_price * 0.70, 2)
        ce_t1 = round(ce_price * 1.50, 2)
        ce_t2 = round(ce_price * 2.00, 2)

        pe_entry = round(pe_price, 2)
        pe_sl = round(pe_price * 0.70, 2)
        pe_t1 = round(pe_price * 1.50, 2)
        pe_t2 = round(pe_price * 2.00, 2)

        # PCR estimation (from price action)
        pcr = self._estimate_pcr(df, spot_price) if df is not None else 1.0

        # Strategy recommendation
        if pcr < 0.9:
            strategy = "BULLISH"
            recommendation = "BUY CE"
            primary_entry = ce_entry
            primary_sl = ce_sl
            primary_t1 = ce_t1
            primary_t2 = ce_t2
            primary_strike = f"{atm} CE"
        elif pcr > 1.2:
            strategy = "BEARISH"
            recommendation = "BUY PE"
            primary_entry = pe_entry
            primary_sl = pe_sl
            primary_t1 = pe_t1
            primary_t2 = pe_t2
            primary_strike = f"{atm} PE"
        else:
            strategy = "NEUTRAL"
            recommendation = "STRADDLE"
            primary_entry = round(ce_price + pe_price, 2)
            primary_sl = round(primary_entry * 0.70, 2)
            primary_t1 = round(primary_entry * 1.30, 2)
            primary_t2 = round(primary_entry * 1.60, 2)
            primary_strike = f"{atm} CE + {atm} PE"

        # Lot value
        lot_value = round(primary_entry * lot_size, 2)

        return {
            "symbol": symbol.upper(),
            "spot_price": round(spot_price, 2),
            "atm_strike": atm,
            "strategy": strategy,
            "recommendation": recommendation,
            "pcr": round(pcr, 2),
            "iv": round(hv * 100, 1),
            "signal": {
                "strike": primary_strike,
                "entry": primary_entry,
                "stop_loss": primary_sl,
                "target_1": primary_t1,
                "target_2": primary_t2,
                "risk_reward": "1:1.67",
                "lot_size": lot_size,
                "lot_value": lot_value,
            },
            "option_chain": {
                "ce": {
                    "atm": {"strike": atm, "price": ce_entry, "greeks": ce_greeks},
                    "itm": {"strike": itm_ce, "price": round(itm_ce_price, 2)},
                    "otm": {"strike": otm_ce, "price": round(otm_ce_price, 2)},
                },
                "pe": {
                    "atm": {"strike": atm, "price": pe_entry, "greeks": pe_greeks},
                    "itm": {"strike": itm_pe, "price": round(itm_pe_price, 2)},
                    "otm": {"strike": otm_pe, "price": round(otm_pe_price, 2)},
                },
            },
            "greeks": {"ce": ce_greeks, "pe": pe_greeks},
            "config": {"lot_size": lot_size, "strike_step": step},
            "timestamp": datetime.now().isoformat(),
        }

    def _estimate_pcr(self, df: pd.DataFrame, spot: float) -> float:
        """Estimate PCR from price action (proxy when real OI unavailable)."""
        if df is None or len(df) < 10:
            return 1.0

        close = df["close"]
        # Use price momentum as PCR proxy
        ret_5d = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6]
        rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1]

        # Higher RSI + positive returns = low PCR (bullish)
        # Lower RSI + negative returns = high PCR (bearish)
        if rsi > 60 and ret_5d > 0.005:
            return round(0.7 + (70 - rsi) * 0.01, 2)  # 0.6-0.8
        elif rsi < 40 and ret_5d < -0.005:
            return round(1.3 + (40 - rsi) * 0.02, 2)  # 1.3-1.7
        else:
            return round(0.9 + (50 - rsi) * 0.006, 2)  # 0.9-1.2

    def get_full_chain(self, spot_price: float, symbol: str, df: pd.DataFrame = None) -> dict:
        """Generate full option chain (5 strikes each side)."""
        config = SYMBOLS.get(symbol.upper(), SYMBOLS.get("NIFTY"))
        step = config["strike_step"]
        atm = round(spot_price / step) * step

        if df is not None and len(df) > 20:
            returns = df["close"].pct_change().dropna()
            hv = float(returns.tail(20).std() * math.sqrt(252))
        else:
            hv = 0.15

        T = 3 / 365
        r = 0.065

        chain = []
        for i in range(-5, 6):
            strike = atm + i * step
            ce_price = self.black_scholes_call(spot_price, strike, T, r, hv)
            pe_price = self.black_scholes_put(spot_price, strike, T, r, hv)

            # OI estimate (higher near ATM)
            dist = abs(i)
            oi_factor = max(0.2, 1 - dist * 0.15)

            chain.append({
                "strike": strike,
                "ce_price": round(ce_price, 2),
                "pe_price": round(pe_price, 2),
                "ce_oi": int(100000 * oi_factor),
                "pe_oi": int(100000 * oi_factor * (1.1 if i > 0 else 0.9)),
                "is_atm": i == 0,
                "is_itm_ce": strike < spot_price,
                "is_itm_pe": strike > spot_price,
            })

        return {
            "symbol": symbol.upper(),
            "spot": round(spot_price, 2),
            "atm_strike": atm,
            "chain": chain,
            "iv": round(hv * 100, 1),
        }
