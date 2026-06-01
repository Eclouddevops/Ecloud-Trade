"""
Ecloud-Trade: Enterprise AI Stock Market Analytics Platform
============================================================
Bloomberg Terminal Style - Live Auto-Refreshing Dashboard

Features:
- Live Market Data (Indian + Global)
- Options CE/PE Signals (NIFTY, BANKNIFTY, SENSEX)
- Candlestick Pattern Scanner (11 patterns)
- Pivot Point Analysis (Classic, Fibonacci, Camarilla)
- Intraday Trading Signals with Entry/SL/Targets
- Technical Indicators (RSI, MACD, EMA, Bollinger, VWAP, ADX)
- Company Fundamentals & Financials
- Backtesting Engine (EMA Cross, RSI, MACD)
- Risk Analysis & Position Sizing
- AI Predictions (XGBoost + Random Forest)
- Smart Buy/Sell/Hold Signals
- Top Opportunities & Alerts
- Global Markets Monitor

Usage:
    python live_dashboard.py
    python live_dashboard.py RELIANCE TCS INFY HDFCBANK SBIN

Opens at: http://localhost:5000 (auto-refreshes every 60s)
Press Ctrl+C to stop.
"""
import sys
import os
import json
import threading
import time
import webbrowser
from datetime import datetime
from flask import Flask, jsonify, Response

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.market_overview import MarketOverview
from data.options_analyzer import OptionsAnalyzer
from data.data_collector import MarketDataCollector
from data.candlestick_patterns import CandlestickPatternDetector
from indicators.technical import TechnicalIndicators
from modules.pivot_analysis import PivotAnalyzer
from modules.intraday_signals import IntradaySignalGenerator
from modules.company_fundamentals import CompanyFundamentals
from modules.backtesting import BacktestEngine
from modules.risk_manager import RiskManager
from modules.global_market import GlobalMarketMonitor
from modules.news_intelligence import NewsIntelligence
from modules.deep_analysis import DeepStockAnalyzer
from modules.broker_integration import BrokerInterface
from modules.breakout_probability import BreakoutProbability
from modules.smart_option_picker import SmartOptionPicker
from config.settings import SAMPLE_STOCKS

app = Flask(__name__)

# Fix numpy serialization
import numpy as np
from flask.json.provider import DefaultJSONProvider
class NumpyJSONProvider(DefaultJSONProvider):
    def default(self, o):
        if isinstance(o, (np.bool_, np.integer)):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)
app.json_provider_class = NumpyJSONProvider
app.json = NumpyJSONProvider(app)

LIVE_DATA = {
    "market": {}, "options": [], "stocks": [], "patterns_scanner": [],
    "alerts": [], "top_opportunities": {"bullish": [], "bearish": []},
    "intraday_signals": [], "pivot_data": [], "global_markets": {},
    "backtests": {}, "smart_picks": {}, "last_updated": "", "update_count": 0,
}
LOCK = threading.Lock()

if len(sys.argv) > 1:
    TRACK_STOCKS = [s.upper() for s in sys.argv[1:]]
else:
    TRACK_STOCKS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN"]

def fetch_live_data():
    """Master data fetcher - called every 60s by background thread."""
    try:
        now = datetime.now().strftime('%H:%M:%S')
        print(f"\n[{now}] ═══ Fetching Live Data ═══")

        overview = MarketOverview()
        collector = MarketDataCollector()
        options_analyzer = OptionsAnalyzer()
        pivot_analyzer = PivotAnalyzer()
        intraday_gen = IntradaySignalGenerator()
        risk_mgr = RiskManager()
        global_monitor = GlobalMarketMonitor()
        alerts = []

        # 1. Market Overview
        print(f"  [1/7] Market indices...")
        market = overview.get_market_summary()

        # 2. Global Markets
        print(f"  [2/7] Global markets...")
        try:
            global_data = global_monitor.get_all()
        except Exception:
            global_data = {}

        # 3. Options Analysis
        print(f"  [3/7] Options CE/PE signals...")
        options = options_analyzer.get_all_indices_analysis()

        # 4. Intraday Signals for indices
        print(f"  [4/7] Intraday signals...")
        intraday_signals = []
        for opt in options:
            if "error" not in opt:
                try:
                    pivots = opt.get("levels", {})
                    ind = opt.get("indicators", {})
                    sig = intraday_gen.generate_option_intraday(
                        opt["index"], opt["current_price"], pivots, ind
                    )
                    intraday_signals.append(sig)
                except Exception as e:
                    print(f"    Intraday signal error for {opt.get('index')}: {e}")

        # 5. Stock Analysis + Patterns + Pivots + Risk
        print(f"  [5/7] Stock analysis ({len(TRACK_STOCKS)} stocks)...")
        stocks = []
        patterns_scanner = []
        pivot_data = []
        bullish_opps, bearish_opps = [], []
        backtest_results = {}

        for symbol in TRACK_STOCKS:
            try:
                df = collector.get_stock_data(symbol, period="6mo")
                info = collector.get_current_price(symbol)
                price = info.get("current_price") or df["close"].iloc[-1]
                prev_close = info.get("previous_close") or df["close"].iloc[-2]
                change_pct = round(((price - prev_close) / prev_close) * 100, 2)

                # Technical Indicators
                tech = TechnicalIndicators(df)
                tech.calculate_all()
                summary = tech.get_indicator_summary()
                sr = tech.get_support_resistance()

                # Pivot Points
                prev_h = df["high"].iloc[-2]
                prev_l = df["low"].iloc[-2]
                prev_c = df["close"].iloc[-2]
                pivots = pivot_analyzer.calculate_pivots(prev_h, prev_l, prev_c)
                fib_pivots = pivot_analyzer.calculate_fibonacci_pivots(prev_h, prev_l, prev_c)
                pivot_signal = pivot_analyzer.get_pivot_signal(
                    price, pivots, summary["rsi"],
                    "Bullish" in summary["macd_signal"]
                )
                pivot_data.append({
                    "symbol": symbol, "price": round(price, 2),
                    "classic": pivots, "fibonacci": fib_pivots,
                    "signal": pivot_signal,
                })

                # Candlestick Patterns
                detector = CandlestickPatternDetector(df)
                detected = detector.detect_all()

                # Risk Analysis
                risk = risk_mgr.calculate_risk_metrics(df, price)

                # Breakout Probability
                bp = BreakoutProbability()
                breakout_data = bp.calculate(df)

                # Composite Score
                score = 0
                if summary["rsi"] < 30: score += 2
                elif summary["rsi"] > 70: score -= 2
                elif summary["rsi"] > 50: score += 0.5
                else: score -= 0.5
                if "Bullish" in summary["macd_signal"]: score += 1.5
                elif "Bearish" in summary["macd_signal"]: score -= 1.5
                if "Strong Bullish" in summary["ma_signal"]: score += 2
                elif "Bullish" in summary["ma_signal"]: score += 1
                elif "Strong Bearish" in summary["ma_signal"]: score -= 2
                elif "Bearish" in summary["ma_signal"]: score -= 1
                if summary["bb_signal"] == "Oversold": score += 1
                elif summary["bb_signal"] == "Overbought": score -= 1
                for p in detected:
                    if "BUY" in p["signal"]: score += 1.5
                    elif "SELL" in p["signal"]: score -= 1.5
                # Pivot boost
                if pivot_signal["signal"] in ("BUY", "STRONG BUY"): score += 1
                elif pivot_signal["signal"] in ("SELL", "STRONG SELL"): score -= 1

                # Alerts
                if summary["volume_ratio"] > 2:
                    alerts.append({"type": "volume", "msg": f"{symbol}: Volume spike {summary['volume_ratio']:.1f}x"})
                if summary["rsi"] > 70:
                    alerts.append({"type": "rsi", "msg": f"{symbol}: RSI {summary['rsi']} Overbought"})
                elif summary["rsi"] < 30:
                    alerts.append({"type": "rsi", "msg": f"{symbol}: RSI {summary['rsi']} Oversold"})
                for p in detected:
                    alerts.append({"type": "pattern", "msg": f"{symbol}: {p['pattern']} ({p['signal']})"})

                # Signal
                if score >= 4: signal = "STRONG BUY"
                elif score >= 2: signal = "BUY"
                elif score <= -4: signal = "STRONG SELL"
                elif score <= -2: signal = "SELL"
                else: signal = "HOLD"

                stocks.append({
                    "symbol": symbol, "price": round(price, 2), "change_pct": change_pct,
                    "signal": signal, "score": round(score, 1),
                    "rsi": summary["rsi"], "rsi_signal": summary["rsi_signal"],
                    "macd_signal": summary["macd_signal"], "ma_signal": summary["ma_signal"],
                    "bb_signal": summary["bb_signal"], "adx": summary["adx"],
                    "trend_strength": summary["trend_strength"],
                    "atr": summary["atr"], "volume_ratio": summary["volume_ratio"],
                    "ema_20": summary["ema_20"], "sma_50": summary["sma_50"], "sma_200": summary["sma_200"],
                    "support_1": sr["support_1"], "resistance_1": sr["resistance_1"],
                    "risk": risk["risk_rating"], "volatility_score": risk["volatility_score"],
                    "max_drawdown": risk["max_drawdown"],
                    "sector": info.get("sector", ""), "patterns": detected,
                    "pivot_signal": pivot_signal["signal"],
                    "breakout": breakout_data,
                })

                for p in detected:
                    patterns_scanner.append({
                        "symbol": symbol, "pattern": p["pattern"],
                        "signal": p["signal"], "confidence": p["confidence"],
                        "type": p["type"], "description": p["description"],
                    })

                if score >= 3:
                    bullish_opps.append({"symbol": symbol, "score": round(score, 1),
                        "pattern": detected[0]["pattern"] if detected else "Technical",
                        "confidence": detected[0]["confidence"] if detected else 70,
                        "target": sr["resistance_1"]})
                elif score <= -3:
                    bearish_opps.append({"symbol": symbol, "score": round(score, 1),
                        "pattern": detected[0]["pattern"] if detected else "Technical",
                        "confidence": detected[0]["confidence"] if detected else 70,
                        "stoploss": sr["resistance_1"]})

                # Backtest (first run only)
                if LIVE_DATA["update_count"] == 0:
                    bt = BacktestEngine(df)
                    backtest_results[symbol] = bt.run_all()

                print(f"    {symbol}: Rs.{price} ({change_pct:+.2f}%) [{signal}]")
            except Exception as e:
                stocks.append({"symbol": symbol, "error": str(e)})
                print(f"    {symbol}: ERROR - {e}")

        # 6. Sort
        print(f"  [6/7] Compiling results...")
        bullish_opps.sort(key=lambda x: x["score"], reverse=True)
        bearish_opps.sort(key=lambda x: x["score"])

        # 7. Update global store
        print(f"  [7/7] Updating dashboard...")
        # Smart Option Picker
        picker = SmartOptionPicker()
        smart_picks = picker.rank_and_recommend(options, market)

        with LOCK:
            LIVE_DATA["market"] = market
            LIVE_DATA["options"] = options
            LIVE_DATA["stocks"] = stocks
            LIVE_DATA["smart_picks"] = smart_picks
            LIVE_DATA["patterns_scanner"] = patterns_scanner
            LIVE_DATA["alerts"] = [a["msg"] for a in alerts[-30:]]
            LIVE_DATA["top_opportunities"] = {"bullish": bullish_opps[:5], "bearish": bearish_opps[:5]}
            LIVE_DATA["intraday_signals"] = intraday_signals
            LIVE_DATA["pivot_data"] = pivot_data
            LIVE_DATA["global_markets"] = global_data
            if backtest_results:
                LIVE_DATA["backtests"] = backtest_results
            LIVE_DATA["last_updated"] = datetime.now().strftime("%d %b %Y, %I:%M:%S %p")
            LIVE_DATA["update_count"] += 1

        print(f"[{now}] ═══ Update #{LIVE_DATA['update_count']} Complete ═══")

    except Exception as e:
        print(f"[ERROR] {e}")


def background_updater(interval=60):
    while True:
        fetch_live_data()
        print(f"    Next refresh in {interval}s...\n")
        time.sleep(interval)


@app.route("/api/live")
def api_live():
    with LOCK:
        return jsonify(LIVE_DATA)


@app.route("/api/company/<symbol>")
def api_company(symbol):
    """Get company fundamentals on demand."""
    try:
        cf = CompanyFundamentals()
        info = cf.get_company_info(symbol.upper())
        financials = cf.get_financials(symbol.upper())
        balance = cf.get_balance_sheet(symbol.upper())
        cashflow = cf.get_cashflow(symbol.upper())
        return jsonify({"info": info, "financials": financials, "balance_sheet": balance, "cashflow": cashflow})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/deep/<symbol>")
def api_deep_analysis(symbol):
    """Get deep AI analysis for a stock."""
    try:
        analyzer = DeepStockAnalyzer()
        result = analyzer.analyze(symbol.upper())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/news")
def api_news():
    """Get market news intelligence."""
    try:
        news = NewsIntelligence()
        return jsonify(news.get_full_news_report())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/news/<symbol>")
def api_news_company(symbol):
    """Get company-specific news."""
    try:
        news = NewsIntelligence()
        return jsonify(news.get_full_news_report(symbol.upper()))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/broker/account")
def api_broker_account():
    """Get broker account info."""
    broker = BrokerInterface()
    return jsonify(broker.get_account_info())


@app.route("/api/broker/positions")
def api_broker_positions():
    """Get current positions."""
    broker = BrokerInterface()
    return jsonify({"positions": broker.get_positions(), "orders": broker.get_orders()})


@app.route("/api/broker/order", methods=["POST"])
def api_broker_order():
    """Place an order (paper trading)."""
    from flask import request
    data = request.get_json()
    broker = BrokerInterface()
    result = broker.place_order(
        symbol=data.get("symbol", ""),
        side=data.get("side", "BUY"),
        qty=data.get("qty", 1),
        order_type=data.get("type", "MARKET"),
        price=data.get("price", 0),
        stop_loss=data.get("stop_loss", 0),
        target=data.get("target", 0),
    )
    return jsonify(result)


@app.route("/api/chart/<path:symbol>")
def api_chart_data(symbol):
    """Get OHLC data with AI-powered BUY CE/PE, EXIT, SL, Target markers on chart."""
    try:
        import yfinance as yf
        import ta as ta_lib
        from flask import request

        period = request.args.get("period", "6mo")

        ticker_symbol = symbol
        if not symbol.startswith("^") and not symbol.endswith(".NS"):
            ticker_symbol = f"{symbol}.NS"
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        if df.empty:
            return jsonify({"error": f"No data for {symbol}"})

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # Indicators
        rsi = ta_lib.momentum.RSIIndicator(close=close, window=14).rsi()
        macd_ind = ta_lib.trend.MACD(close=close)
        macd_line = macd_ind.macd()
        macd_signal_line = macd_ind.macd_signal()
        macd_hist = macd_ind.macd_diff()
        ema_9 = ta_lib.trend.EMAIndicator(close=close, window=9).ema_indicator()
        ema_21 = ta_lib.trend.EMAIndicator(close=close, window=21).ema_indicator()
        ema_50 = ta_lib.trend.EMAIndicator(close=close, window=50).ema_indicator()
        bb = ta_lib.volatility.BollingerBands(close=close, window=20, window_dev=2)
        bb_upper = bb.bollinger_hband()
        bb_lower = bb.bollinger_lband()
        atr = ta_lib.volatility.AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
        adx_ind = ta_lib.trend.ADXIndicator(high=high, low=low, close=close, window=14)
        adx = adx_ind.adx()
        adx_pos = adx_ind.adx_pos()
        adx_neg = adx_ind.adx_neg()
        stoch = ta_lib.momentum.StochasticOscillator(high=high, low=low, close=close)
        stoch_k = stoch.stoch()
        vol_sma = volume.rolling(20).mean()

        candles = []
        markers = []
        # Track open position for EXIT signals
        in_position = None  # 'CE' or 'PE' or None
        entry_price = 0
        entry_atr = 0

        for i, (idx, row) in enumerate(df.iterrows()):
            candles.append({
                "time": idx.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
            })

            if i < 26:
                continue

            cur = close.iloc[i]
            prev = close.iloc[i - 1]
            cur_rsi = rsi.iloc[i]
            prev_rsi = rsi.iloc[i - 1]
            cur_macd = macd_line.iloc[i]
            cur_macd_sig = macd_signal_line.iloc[i]
            prev_macd = macd_line.iloc[i - 1]
            prev_macd_sig = macd_signal_line.iloc[i - 1]
            cur_ema9 = ema_9.iloc[i]
            cur_ema21 = ema_21.iloc[i]
            prev_ema9 = ema_9.iloc[i - 1]
            prev_ema21 = ema_21.iloc[i - 1]
            cur_adx = adx.iloc[i]
            cur_adx_pos = adx_pos.iloc[i]
            cur_adx_neg = adx_neg.iloc[i]
            cur_atr = atr.iloc[i]
            cur_vol = volume.iloc[i]
            avg_vol = vol_sma.iloc[i] if vol_sma.iloc[i] > 0 else 1
            vol_spike = cur_vol > avg_vol * 1.3
            cur_stoch = stoch_k.iloc[i]
            cur_bb_up = bb_upper.iloc[i]
            cur_bb_low = bb_lower.iloc[i]

            # Skip if any indicator is NaN
            import math
            vals = [cur_rsi, cur_macd, cur_macd_sig, cur_ema9, cur_ema21, cur_adx, cur_atr]
            if any(v != v for v in vals):  # NaN check
                continue

            # ═══ SCORING SYSTEM ═══
            # Positive = Bullish (CE), Negative = Bearish (PE)
            score = 0

            # EMA Crossover (weight: 3)
            if prev_ema9 <= prev_ema21 and cur_ema9 > cur_ema21:
                score += 3  # Fresh bullish cross
            elif prev_ema9 >= prev_ema21 and cur_ema9 < cur_ema21:
                score -= 3  # Fresh bearish cross
            elif cur_ema9 > cur_ema21:
                score += 1
            else:
                score -= 1

            # MACD (weight: 2)
            if prev_macd <= prev_macd_sig and cur_macd > cur_macd_sig:
                score += 2  # Bullish crossover
            elif prev_macd >= prev_macd_sig and cur_macd < cur_macd_sig:
                score -= 2  # Bearish crossover
            elif cur_macd > cur_macd_sig:
                score += 0.5
            else:
                score -= 0.5

            # RSI (weight: 2)
            if prev_rsi < 30 and cur_rsi > 30:
                score += 2  # Oversold bounce
            elif prev_rsi > 70 and cur_rsi < 70:
                score -= 2  # Overbought drop
            elif cur_rsi > 55:
                score += 0.5
            elif cur_rsi < 45:
                score -= 0.5

            # ADX Trend (weight: 1.5)
            if cur_adx > 25 and cur_adx_pos > cur_adx_neg:
                score += 1.5
            elif cur_adx > 25 and cur_adx_neg > cur_adx_pos:
                score -= 1.5

            # Volume confirmation (weight: 1)
            if vol_spike and cur > prev:
                score += 1
            elif vol_spike and cur < prev:
                score -= 1

            # Bollinger (weight: 1)
            if cur < cur_bb_low:
                score += 1  # Oversold
            elif cur > cur_bb_up:
                score -= 1  # Overbought

            # Stochastic (weight: 1)
            if cur_stoch < 20:
                score += 1
            elif cur_stoch > 80:
                score -= 1

            # ═══ GENERATE SIGNALS ═══
            time_str = idx.strftime("%Y-%m-%d")

            # EXIT existing position
            if in_position == 'CE':
                sl = entry_price - entry_atr * 1.5
                t1 = entry_price + entry_atr * 1.5
                t2 = entry_price + entry_atr * 2.5
                t3 = entry_price + entry_atr * 3.5
                if cur <= sl or score <= -3:
                    markers.append({"time": time_str, "position": "aboveBar", "color": "#ff9100", "shape": "circle", "text": "EXIT CE"})
                    in_position = None
                elif cur >= t3:
                    markers.append({"time": time_str, "position": "aboveBar", "color": "#00bcd4", "shape": "circle", "text": "EXIT T3"})
                    in_position = None

            elif in_position == 'PE':
                sl = entry_price + entry_atr * 1.5
                t1 = entry_price - entry_atr * 1.5
                t2 = entry_price - entry_atr * 2.5
                t3 = entry_price - entry_atr * 3.5
                if cur >= sl or score >= 3:
                    markers.append({"time": time_str, "position": "belowBar", "color": "#ff9100", "shape": "circle", "text": "EXIT PE"})
                    in_position = None
                elif cur <= t3:
                    markers.append({"time": time_str, "position": "belowBar", "color": "#00bcd4", "shape": "circle", "text": "EXIT T3"})
                    in_position = None

            # NEW ENTRY signals (only if not in position)
            if in_position is None:
                if score >= 5:
                    markers.append({"time": time_str, "position": "belowBar", "color": "#00ff88", "shape": "arrowUp", "text": "STRONG CE"})
                    in_position = 'CE'
                    entry_price = cur
                    entry_atr = cur_atr
                elif score >= 3:
                    markers.append({"time": time_str, "position": "belowBar", "color": "#00e676", "shape": "arrowUp", "text": "BUY CE"})
                    in_position = 'CE'
                    entry_price = cur
                    entry_atr = cur_atr
                elif score <= -5:
                    markers.append({"time": time_str, "position": "aboveBar", "color": "#ff1744", "shape": "arrowDown", "text": "STRONG PE"})
                    in_position = 'PE'
                    entry_price = cur
                    entry_atr = cur_atr
                elif score <= -3:
                    markers.append({"time": time_str, "position": "aboveBar", "color": "#ff5252", "shape": "arrowDown", "text": "BUY PE"})
                    in_position = 'PE'
                    entry_price = cur
                    entry_atr = cur_atr

        # Add price lines for current position levels
        lines = []
        if in_position and entry_price > 0:
            cur_atr_val = atr.iloc[-1]
            if in_position == 'CE':
                lines.append({"price": round(entry_price - cur_atr_val * 1.5, 2), "color": "#ff5252", "label": "STOP LOSS"})
                lines.append({"price": round(entry_price + cur_atr_val * 1.5, 2), "color": "#00e676", "label": "TARGET 1"})
                lines.append({"price": round(entry_price + cur_atr_val * 2.5, 2), "color": "#69f0ae", "label": "TARGET 2"})
                lines.append({"price": round(entry_price + cur_atr_val * 3.5, 2), "color": "#00ff88", "label": "TARGET 3"})
            else:
                lines.append({"price": round(entry_price + cur_atr_val * 1.5, 2), "color": "#ff5252", "label": "STOP LOSS"})
                lines.append({"price": round(entry_price - cur_atr_val * 1.5, 2), "color": "#00e676", "label": "TARGET 1"})
                lines.append({"price": round(entry_price - cur_atr_val * 2.5, 2), "color": "#69f0ae", "label": "TARGET 2"})
                lines.append({"price": round(entry_price - cur_atr_val * 3.5, 2), "color": "#00ff88", "label": "TARGET 3"})

        return jsonify({"candles": candles, "markers": markers, "lines": lines, "position": in_position or "NONE"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/")
def index():
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "live_dashboard.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/html")


if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  Ecloud-Trade: Enterprise AI Stock Market Analytics Platform")
    print("  Bloomberg Terminal Style - Live Dashboard")
    print("=" * 65)
    print(f"  Stocks: {', '.join(TRACK_STOCKS)}")
    print(f"  Options: NIFTY | BANKNIFTY | SENSEX")
    print(f"  Features: Patterns | Pivots | Intraday | Risk | Backtest | AI")
    print(f"  Refresh: Every 60 seconds")
    print(f"  URL: http://localhost:5000")
    print("=" * 65)
    print("  Press Ctrl+C to stop.\n")

    t = threading.Thread(target=background_updater, args=(60,), daemon=True)
    t.start()
    time.sleep(3)
    webbrowser.open("http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
