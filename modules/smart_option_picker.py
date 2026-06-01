"""
Smart Option Picker & Ranking Engine
Compares NIFTY, BANKNIFTY, SENSEX and recommends:
- Best index to trade
- CE or PE direction
- Strike price (low/medium/high premium)
- Expected points gain
- Entry, SL, Exit levels
- Confidence score
"""
import numpy as np


class SmartOptionPicker:
    """Ranks indices and generates complete option trade recommendations."""

    def rank_and_recommend(self, options_data: list, market_data: dict = None) -> dict:
        """
        Compare all indices and generate ranked recommendations.

        Args:
            options_data: List of options analysis results from OptionsAnalyzer
            market_data: Market overview data (for news sentiment)

        Returns:
            Complete recommendation with ranking, strikes, premiums, expected gains
        """
        rankings = []

        for opt in options_data:
            if "error" in opt or not opt.get("recommendation"):
                continue

            rec = opt["recommendation"]
            ind = opt.get("indicators", {})
            vol = opt.get("volatility", {})
            mom = opt.get("momentum", {})
            levels = opt.get("levels", {})
            price = opt["current_price"]

            # ═══ TRADE OPPORTUNITY SCORE (0-100) ═══
            score = 0
            reasons = []

            # 1. Trend Strength (ADX) — max 15 pts
            adx = ind.get("adx", 0)
            if adx > 30:
                score += 15
                reasons.append(f"Strong trend (ADX {adx})")
            elif adx > 25:
                score += 10
                reasons.append(f"Moderate trend (ADX {adx})")
            else:
                score += 3

            # 2. Directional clarity — max 15 pts
            abs_score = abs(rec.get("score", 0))
            dir_pts = min(15, int(abs_score * 2.5))
            score += dir_pts
            if abs_score >= 4:
                reasons.append(f"Clear direction (score {rec['score']})")

            # 3. VWAP Distance — max 10 pts
            vwap = ind.get("vwap", price)
            vwap_dist = abs(price - vwap) / price * 100
            if ind.get("price_vs_vwap") == "Above" and rec.get("side") == "CE":
                score += 10
                reasons.append("Price above VWAP (bullish)")
            elif ind.get("price_vs_vwap") == "Below" and rec.get("side") == "PE":
                score += 10
                reasons.append("Price below VWAP (bearish)")
            else:
                score += 3

            # 4. EMA alignment — max 10 pts
            if ind.get("ema_trend") == "Bullish" and rec.get("side") == "CE":
                score += 10
                reasons.append("EMA bullish alignment")
            elif ind.get("ema_trend") == "Bearish" and rec.get("side") == "PE":
                score += 10
                reasons.append("EMA bearish alignment")
            else:
                score += 2

            # 5. RSI confirmation — max 10 pts
            rsi = ind.get("rsi", 50)
            if rec.get("side") == "CE" and 45 < rsi < 70:
                score += 10
                reasons.append(f"RSI {rsi} supports CE")
            elif rec.get("side") == "PE" and 30 < rsi < 55:
                score += 10
                reasons.append(f"RSI {rsi} supports PE")
            elif rsi < 30 and rec.get("side") == "CE":
                score += 8
                reasons.append(f"RSI {rsi} oversold bounce")
            elif rsi > 70 and rec.get("side") == "PE":
                score += 8
                reasons.append(f"RSI {rsi} overbought drop")
            else:
                score += 2

            # 6. MACD confirmation — max 10 pts
            if ind.get("macd_crossover") == "Bullish" and rec.get("side") == "CE":
                score += 10
                reasons.append("MACD bullish crossover")
            elif ind.get("macd_crossover") == "Bearish" and rec.get("side") == "PE":
                score += 10
                reasons.append("MACD bearish crossover")
            else:
                score += 2

            # 7. Stochastic — max 5 pts
            stoch = ind.get("stochastic_signal", "Neutral")
            if stoch == "Oversold" and rec.get("side") == "CE":
                score += 5
                reasons.append("Stochastic oversold")
            elif stoch == "Overbought" and rec.get("side") == "PE":
                score += 5
                reasons.append("Stochastic overbought")

            # 8. Volatility (ATR) — max 10 pts (higher ATR = more points potential)
            atr = ind.get("atr", 0)
            atr_pct = (atr / price) * 100 if price > 0 else 0
            if atr_pct > 1.0:
                score += 10
                reasons.append(f"High volatility (ATR {atr_pct:.1f}%)")
            elif atr_pct > 0.6:
                score += 7
            else:
                score += 3

            # 9. Momentum — max 10 pts
            ret_1d = mom.get("return_1d", 0)
            if rec.get("side") == "CE" and ret_1d > 0.3:
                score += 10
                reasons.append(f"Bullish momentum +{ret_1d}%")
            elif rec.get("side") == "PE" and ret_1d < -0.3:
                score += 10
                reasons.append(f"Bearish momentum {ret_1d}%")
            else:
                score += 3

            # 10. Confidence from original analysis — max 5 pts
            conf = rec.get("confidence", "Low")
            if conf == "High":
                score += 5
            elif conf == "Medium":
                score += 3

            score = min(100, score)

            # ═══ EXPECTED POINTS GAIN ═══
            expected_move = vol.get("expected_daily_move", atr)
            if rec.get("side") in ("CE", "PE"):
                expected_points = round(expected_move * 1.2, 0)  # Slightly optimistic
            else:
                expected_points = 0

            # ═══ STRIKE PRICE RECOMMENDATIONS ═══
            atm = levels.get("atm_strike", round(price / 50) * 50)
            step = 50 if "NIFTY" in opt["index"] else 100

            strikes = self._calculate_strikes(
                price, atm, step, rec.get("side", "WAIT"), atr, expected_points
            )

            # ═══ ENTRY / SL / EXIT ═══
            side = rec.get("side", "WAIT")
            if side == "CE":
                entry = round(price + atr * 0.2, 2)
                sl = round(price - atr * 1.2, 2)
                exit_price = round(price + expected_points, 2)
            elif side == "PE":
                entry = round(price - atr * 0.2, 2)
                sl = round(price + atr * 1.2, 2)
                exit_price = round(price - expected_points, 2)
            else:
                entry = round(price, 2)
                sl = 0
                exit_price = 0

            rankings.append({
                "index": opt["index"],
                "price": round(price, 2),
                "side": side,
                "action": rec.get("action", "WAIT"),
                "score": score,
                "confidence": f"{score}%",
                "expected_points": int(expected_points),
                "expected_option_gain_pct": round(expected_points / max(atr, 1) * 15, 0),
                "entry": entry,
                "stop_loss": sl,
                "exit": exit_price,
                "atr": round(atr, 2),
                "strikes": strikes,
                "reasons": reasons[:6],
                "indicators_summary": {
                    "adx": adx,
                    "rsi": rsi,
                    "macd": ind.get("macd_crossover"),
                    "ema": ind.get("ema_trend"),
                    "vwap": ind.get("price_vs_vwap"),
                    "stochastic": stoch,
                },
            })

        # Sort by score (best first)
        rankings.sort(key=lambda x: x["score"], reverse=True)

        # Best trade
        best = rankings[0] if rankings else None

        return {
            "rankings": rankings,
            "best_trade": best,
            "timestamp": None,  # Will be set by caller
        }

    def _calculate_strikes(self, price, atm, step, side, atr, expected_points):
        """Calculate strike recommendations for different premium levels."""
        if side == "CE":
            # ITM (high premium), ATM (medium), OTM (low premium)
            itm_strike = atm - step
            atm_strike = atm
            otm_strike = atm + step
            deep_otm = atm + step * 2

            return {
                "conservative": {
                    "strike": itm_strike,
                    "type": "ITM CE",
                    "premium_range": "₹300-₹500+",
                    "risk": "Low",
                    "expected_gain": f"+{int(expected_points * 0.7)} pts in premium",
                },
                "moderate": {
                    "strike": atm_strike,
                    "type": "ATM CE",
                    "premium_range": "₹150-₹300",
                    "risk": "Medium",
                    "expected_gain": f"+{int(expected_points * 0.5)} pts in premium",
                },
                "aggressive": {
                    "strike": otm_strike,
                    "type": "OTM CE",
                    "premium_range": "₹50-₹150",
                    "risk": "High",
                    "expected_gain": f"+{int(expected_points * 0.3)} pts (high % gain)",
                },
            }
        elif side == "PE":
            itm_strike = atm + step
            atm_strike = atm
            otm_strike = atm - step

            return {
                "conservative": {
                    "strike": itm_strike,
                    "type": "ITM PE",
                    "premium_range": "₹300-₹500+",
                    "risk": "Low",
                    "expected_gain": f"+{int(expected_points * 0.7)} pts in premium",
                },
                "moderate": {
                    "strike": atm_strike,
                    "type": "ATM PE",
                    "premium_range": "₹150-₹300",
                    "risk": "Medium",
                    "expected_gain": f"+{int(expected_points * 0.5)} pts in premium",
                },
                "aggressive": {
                    "strike": otm_strike,
                    "type": "OTM PE",
                    "premium_range": "₹50-₹150",
                    "risk": "High",
                    "expected_gain": f"+{int(expected_points * 0.3)} pts (high % gain)",
                },
            }
        else:
            return {}
