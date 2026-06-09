"""
Flask Web Application
Provides a web interface and REST API for the stock analysis system.
Includes a chatbot for conversational stock recommendations.
Includes USA news, president updates, and chart data with support/resistance.
Includes options trading signals, intraday signals, candlestick scanner, and breakout probability.
"""
import json
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from analysis.analyzer import StockAnalyzer
from data.usa_news import USANewsAnalyzer
from data.data_collector import MarketDataCollector
from data.options_analyzer import OptionsAnalyzer
from data.candlestick_patterns import CandlestickPatternDetector
from indicators.technical import TechnicalIndicators
from modules.breakout_probability import BreakoutProbability
from modules.intraday_signals import IntradaySignalGenerator
from modules.gainzalgo import GainzAlgoV2Alpha
from modules.smart_predictions import SmartPredictor
from modules.ai_decision_engine import AIDecisionEngine
from modules.broker_adapters import BrokerManager
from modules.nse_live import NSELiveData
from modules.quantedge import QuantEdgeEngine
from werkzeug.middleware.proxy_fix import ProxyFix
from config.settings import FLASK_SECRET_KEY, FLASK_DEBUG, FLASK_PORT, SAMPLE_STOCKS

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = FLASK_SECRET_KEY
app.config['JSON_SORT_KEYS'] = False

# ─── WebSocket Setup ────────────────────────────────────────────────────────────
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ─── Visit Counter ──────────────────────────────────────────────────────────────
import os as _os
_counter_file = _os.path.join(_os.path.dirname(__file__), "data", "cache", "visit_counter.json")

def _load_counter():
    try:
        with open(_counter_file, "r") as f:
            return json.load(f)
    except Exception:
        return {"total_visits": 0, "page_views": 0}

def _save_counter(data):
    try:
        with open(_counter_file, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

visit_data = _load_counter()


# Fix NaN in JSON responses
import math as _math


def _sanitize_for_json(obj):
    """Recursively sanitize data for JSON serialization (removes NaN/Infinity)."""
    if isinstance(obj, float):
        if _math.isnan(obj) or _math.isinf(obj):
            return 0
        return obj
    elif isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    else:
        try:
            import numpy as np
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                if np.isnan(obj) or np.isinf(obj):
                    return 0
                return float(obj)
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
        except (ImportError, TypeError):
            pass
    return obj


def safe_jsonify(data):
    """jsonify wrapper that handles NaN and numpy types."""
    return jsonify(_sanitize_for_json(data))

analyzer = StockAnalyzer()
usa_news_analyzer = USANewsAnalyzer()
data_collector = MarketDataCollector()
options_analyzer = OptionsAnalyzer()
breakout_calc = BreakoutProbability()
intraday_gen = IntradaySignalGenerator()
gainzalgo = GainzAlgoV2Alpha()
smart_predictor = SmartPredictor()
ai_engine = AIDecisionEngine()
broker_mgr = BrokerManager()
nse_live = NSELiveData()
quantedge = QuantEdgeEngine()

# Store recent analyses for chatbot context
_chat_analysis_cache = {}
_usa_news_cache = {}


@app.route("/")
def index():
    """Home page with stock selection."""
    visit_data["total_visits"] += 1
    visit_data["page_views"] += 1
    _save_counter(visit_data)
    return render_template("index.html", stocks=SAMPLE_STOCKS, visits=visit_data["total_visits"], page_views=visit_data["page_views"])


@app.route("/analyze", methods=["POST"])
def analyze_stock():
    """
    Analyze a stock and return results.

    Request JSON:
        {"symbol": "RELIANCE", "train": true}

    Returns:
        Complete analysis JSON
    """
    data = request.get_json()
    symbol = data.get("symbol", "").upper().strip()
    train = data.get("train", True)

    if not symbol:
        return jsonify({"error": "Stock symbol is required"}), 400

    try:
        result = analyzer.analyze(symbol, train_model=train)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@app.route("/api/quick-analysis/<symbol>")
def quick_analysis(symbol: str):
    """
    Quick analysis without retraining models.

    Args:
        symbol: Stock symbol in URL path
    """
    try:
        result = analyzer.analyze(symbol.upper(), train_model=False)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stocks")
def list_stocks():
    """Return list of available sample stocks."""
    return jsonify({"stocks": SAMPLE_STOCKS})


@app.route("/api/health")
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "Ecloud-Trade Market Analyzer"})


@app.route("/api/usa-news")
def usa_news():
    """
    Get comprehensive USA news analysis including president updates,
    Fed policy, trade news, and US market data with India impact assessment.
    """
    try:
        result = usa_news_analyzer.get_complete_usa_analysis()
        _usa_news_cache["latest"] = result
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch USA news: {str(e)}"}), 500


@app.route("/api/usa-president")
def usa_president():
    """Get US President-specific news and policy impact on Indian markets."""
    try:
        result = usa_news_analyzer.get_president_news()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/usa-markets")
def usa_markets():
    """Get US market indices (S&P 500, NASDAQ, Dow, VIX) and India impact."""
    try:
        result = usa_news_analyzer.get_usa_market_data()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chart-data/<symbol>")
def chart_data(symbol: str):
    """
    Get price chart data with support and resistance levels for plotting.

    Args:
        symbol: Stock symbol (e.g., RELIANCE)

    Returns:
        JSON with OHLCV data and support/resistance levels
    """
    try:
        symbol = symbol.upper()
        df = data_collector.get_stock_data(symbol, period="6mo")

        # Calculate technical indicators for support/resistance
        tech = TechnicalIndicators(df)
        df_with_indicators = tech.calculate_all()
        support_resistance = tech.get_support_resistance()

        # Prepare chart data (last 90 days)
        chart_df = df.tail(90).copy()
        chart_df.index = chart_df.index.strftime("%Y-%m-%d")

        chart_data_list = []
        for date, row in chart_df.iterrows():
            chart_data_list.append({
                "date": date,
                "open": round(row["open"], 2),
                "high": round(row["high"], 2),
                "low": round(row["low"], 2),
                "close": round(row["close"], 2),
                "volume": int(row["volume"]),
            })

        # Get EMA/SMA for overlay on chart
        ema_20 = df_with_indicators["ema_20"].tail(90).tolist()
        sma_50 = df_with_indicators["sma_50"].tail(90).tolist()

        return jsonify({
            "symbol": symbol,
            "chart_data": chart_data_list,
            "support_resistance": support_resistance,
            "moving_averages": {
                "ema_20": [round(v, 2) if not (v != v) else None for v in ema_20],
                "sma_50": [round(v, 2) if not (v != v) else None for v in sma_50],
            },
            "current_price": round(df["close"].iloc[-1], 2),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/options-with-usa")
def options_with_usa():
    """
    Get options analysis enhanced with USA news sentiment.
    Adjusts CE/PE recommendation based on US market cues.
    """
    try:
        import math

        # Get base options analysis
        index_name = request.args.get("index", "NIFTY").upper()
        options_result = options_analyzer.analyze_index_options(index_name)

        # Get USA news impact
        try:
            usa_data = usa_news_analyzer.get_complete_usa_analysis()
            _usa_news_cache["latest"] = usa_data
            usa_score = usa_data.get("combined_score", 0)
        except Exception:
            usa_data = {"combined_score": 0, "usa_news": {"overall_sentiment": "N/A"}, "president_news": {"sentiment": "N/A"}, "us_markets": {}, "options_bias": "Neutral", "recommendation": ""}
            usa_score = 0

        # Sanitize scores (replace NaN/None with 0)
        original_score = options_result.get("recommendation", {}).get("score", 0)
        if original_score is None or (isinstance(original_score, float) and math.isnan(original_score)):
            original_score = 0
        if usa_score is None or (isinstance(usa_score, float) and math.isnan(usa_score)):
            usa_score = 0

        # USA sentiment adds/subtracts up to 2 points from options score
        usa_adjustment = max(-2, min(2, float(usa_score) * 10))
        adjusted_score = float(original_score) + usa_adjustment

        # Recalculate side based on adjusted score
        if adjusted_score >= 4:
            adjusted_side, confidence = "CE", "High"
        elif adjusted_score >= 2:
            adjusted_side, confidence = "CE", "Medium"
        elif adjusted_score <= -4:
            adjusted_side, confidence = "PE", "High"
        elif adjusted_score <= -2:
            adjusted_side, confidence = "PE", "Medium"
        else:
            adjusted_side, confidence = "NEUTRAL", "Low"

        enhanced_result = {
            "options_analysis": options_result,
            "usa_impact": {
                "usa_sentiment": usa_data.get("usa_news", {}).get("overall_sentiment", "N/A"),
                "usa_score": round(float(usa_score), 4),
                "president_sentiment": usa_data.get("president_news", {}).get("sentiment", "N/A"),
                "us_market_mood": usa_data.get("us_markets", {}).get("us_market_mood", "Unknown"),
                "adjustment_applied": round(usa_adjustment, 2),
                "options_bias": usa_data.get("options_bias", "Neutral"),
            },
            "adjusted_recommendation": {
                "side": adjusted_side,
                "action": f"BUY {adjusted_side}" if adjusted_side != "NEUTRAL" else "NO TRADE - WAIT",
                "confidence": confidence,
                "original_score": round(float(original_score), 1),
                "adjusted_score": round(float(adjusted_score), 1),
                "reason": f"Original score {original_score:.1f} adjusted by {usa_adjustment:+.1f} based on USA cues",
            },
            "usa_recommendation": usa_data.get("recommendation", ""),
        }

        return safe_jsonify(enhanced_result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/candlestick-scan/<symbol>")
def candlestick_scan(symbol: str):
    """
    Scan for candlestick patterns on a stock/index.
    Returns detected patterns with confidence and signal.
    """
    try:
        symbol = symbol.upper()
        df = data_collector.get_stock_data(symbol, period="3mo")

        detector = CandlestickPatternDetector(df)
        patterns = detector.detect_all()

        return jsonify({
            "symbol": symbol,
            "patterns_detected": len(patterns),
            "patterns": patterns,
            "current_price": round(df["close"].iloc[-1], 2),
            "last_candle": {
                "open": round(df["open"].iloc[-1], 2),
                "high": round(df["high"].iloc[-1], 2),
                "low": round(df["low"].iloc[-1], 2),
                "close": round(df["close"].iloc[-1], 2),
                "type": "Bullish" if df["close"].iloc[-1] > df["open"].iloc[-1] else "Bearish",
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/intraday-signal/<symbol>")
def intraday_signal(symbol: str):
    """
    Generate intraday trading signal with entry, SL, targets.
    Works for stocks and indices.
    """
    try:
        symbol = symbol.upper()
        is_index = symbol in ("NIFTY", "NIFTY50", "BANKNIFTY", "SENSEX", "FINNIFTY")
        df = data_collector.get_stock_data(symbol, period="6mo")

        import ta as ta_lib
        current_price = df["close"].iloc[-1]

        # Calculate pivots
        prev_h = df["high"].iloc[-2]
        prev_l = df["low"].iloc[-2]
        prev_c = df["close"].iloc[-2]
        pivot = (prev_h + prev_l + prev_c) / 3
        r1 = 2 * pivot - prev_l
        r2 = pivot + (prev_h - prev_l)
        s1 = 2 * pivot - prev_h
        s2 = pivot - (prev_h - prev_l)

        pivots = {"pivot": round(pivot, 2), "r1": round(r1, 2), "r2": round(r2, 2),
                  "s1": round(s1, 2), "s2": round(s2, 2)}

        # Calculate indicators
        rsi = ta_lib.momentum.RSIIndicator(close=df["close"], window=14).rsi().iloc[-1]
        macd_ind = ta_lib.trend.MACD(close=df["close"])
        macd_val = macd_ind.macd().iloc[-1]
        macd_sig = macd_ind.macd_signal().iloc[-1]
        vol_sma = df["volume"].rolling(20).mean().iloc[-1]
        vol_ratio = df["volume"].iloc[-1] / vol_sma if vol_sma > 0 else 1

        indicators = {
            "rsi": round(rsi, 2),
            "macd_crossover": "Bullish" if macd_val > macd_sig else "Bearish",
            "volume_ratio": round(vol_ratio, 2),
        }

        # Generate signal
        if is_index:
            signal = intraday_gen.generate_option_intraday(symbol, current_price, pivots, indicators)
        else:
            signal = intraday_gen.generate_intraday_signal(symbol, current_price, pivots, indicators)

        signal["pivots"] = pivots
        return jsonify(signal)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/breakout/<symbol>")
def breakout_probability(symbol: str):
    """Calculate breakout probability for a stock/index."""
    try:
        symbol = symbol.upper()
        df = data_collector.get_stock_data(symbol, period="6mo")

        result = breakout_calc.calculate(df)
        result["symbol"] = symbol
        result["current_price"] = round(df["close"].iloc[-1], 2)
        return safe_jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/best-trade-today")
def best_trade_today():
    """
    Smart Ranking Engine: Compare NIFTY, BANKNIFTY, SENSEX and recommend
    the best trade today with strike, entry, SL, target.
    """
    try:
        import ta as ta_lib

        indices = ["NIFTY", "BANKNIFTY", "SENSEX"]
        rankings = []

        for name in indices:
            try:
                df = data_collector.get_stock_data(name, period="6mo")
                if df.empty or len(df) < 30:
                    continue

                current_price = df["close"].iloc[-1]

                # Breakout
                bp = breakout_calc.calculate(df)

                # Indicators
                rsi = ta_lib.momentum.RSIIndicator(close=df["close"], window=14).rsi().iloc[-1]
                macd_ind = ta_lib.trend.MACD(close=df["close"])
                macd_val = macd_ind.macd().iloc[-1]
                macd_sig = macd_ind.macd_signal().iloc[-1]
                atr = ta_lib.volatility.AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14).average_true_range().iloc[-1]
                vol_sma = df["volume"].rolling(20).mean().iloc[-1]
                vol_ratio = df["volume"].iloc[-1] / vol_sma if vol_sma > 0 else 1

                # Pivots
                prev_h, prev_l, prev_c = df["high"].iloc[-2], df["low"].iloc[-2], df["close"].iloc[-2]
                pivot = (prev_h + prev_l + prev_c) / 3
                r1 = 2 * pivot - prev_l
                s1 = 2 * pivot - prev_h

                # Score
                score = 0
                direction = "CE"
                if rsi > 55: score += 15
                elif rsi < 45: score -= 15; direction = "PE"
                if macd_val > macd_sig: score += 20
                else: score -= 20; direction = "PE"
                if current_price > pivot: score += 15
                else: score -= 15
                if vol_ratio > 1.2: score += 10
                score += int(bp["breakout_probability"] * 0.4)

                if score < 0:
                    direction = "PE"

                # Strike
                step = 100 if name == "BANKNIFTY" else 50
                strike = round(current_price / step) * step

                # Expected move
                expected_points = round(atr * 1.5, 0)
                premium_est = round(atr * 0.6, 0)

                # Entry/SL/Target
                if direction == "CE":
                    entry = round(current_price + 20, 0)
                    sl = round(s1, 0)
                    target = round(r1, 0)
                else:
                    entry = round(current_price - 20, 0)
                    sl = round(r1, 0)
                    target = round(s1, 0)

                confidence = min(95, max(30, 50 + abs(score)))

                rankings.append({
                    "index": name,
                    "current_price": round(current_price, 2),
                    "direction": f"BUY {direction}",
                    "strike": f"{strike} {direction}",
                    "premium_est": f"₹{premium_est}",
                    "expected_points": f"+{expected_points}",
                    "entry": entry,
                    "stop_loss": sl,
                    "target": target,
                    "confidence": confidence,
                    "score": abs(score),
                    "risk_reward": f"1:{round(abs(target - entry) / max(1, abs(entry - sl)), 1)}",
                    "breakout_prob": bp["breakout_probability"],
                    "vol_ratio": round(vol_ratio, 2),
                    "rsi": round(rsi, 1),
                })
            except Exception:
                continue

        # Sort by score
        rankings.sort(key=lambda x: x["score"], reverse=True)

        best = rankings[0] if rankings else None
        return jsonify({
            "best_trade": best,
            "all_rankings": rankings,
            "recommendation": f"Trade {best['index']} - {best['direction']} @ {best['strike']}" if best else "No clear trade today",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/gainzalgo/<symbol>")
def gainzalgo_signal(symbol: str):
    """
    GainzAlgo V2 Alpha indicator analysis.
    Combines momentum, trend, volatility, volume, structure, and MTF confluence.
    Returns BUY/SELL signal with entry, exit, targets, and expected points.
    """
    try:
        symbol = symbol.upper()
        df = data_collector.get_stock_data(symbol, period="6mo")
        result = gainzalgo.analyze(df, symbol)
        return safe_jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tomorrow/<symbol>")
def tomorrow_prediction(symbol: str):
    """Predict next trading day movement with probability and expected range."""
    try:
        symbol = symbol.upper()
        df = data_collector.get_stock_data(symbol, period="6mo")
        result = smart_predictor.predict_tomorrow(df, symbol)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/smart-trade/<symbol>")
def smart_trade(symbol: str):
    """Generate complete AI trade setup with entry, targets, SL, probability."""
    try:
        symbol = symbol.upper()
        df = data_collector.get_stock_data(symbol, period="6mo")
        result = smart_predictor.generate_smart_trade(df, symbol)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sentiment/<symbol>")
def market_sentiment(symbol: str):
    """Calculate Fear & Greed index for a symbol."""
    try:
        symbol = symbol.upper()
        df = data_collector.get_stock_data(symbol, period="6mo")
        result = smart_predictor.calculate_sentiment(df)
        result["symbol"] = symbol
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/deep-analysis/<symbol>")
def deep_analysis(symbol: str):
    """
    AI Decision Engine — resolves conflicting signals using priority logic.
    Provides unified verdict with full conflict resolution log.
    """
    try:
        symbol = symbol.upper()
        df = data_collector.get_stock_data(symbol, period="6mo")
        result = ai_engine.deep_analysis(df, symbol)
        return safe_jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/live-prices")
def live_prices():
    """
    Real-time prices from NSE India (primary) or broker API (if configured).
    No API key needed for NSE direct data.
    Falls back to broker/Yahoo only if NSE fails.
    """
    try:
        # Try NSE Live first (free, real-time)
        result = nse_live.get_live_prices()
        if "error" not in result and ("NIFTY" in result or "BANKNIFTY" in result):
            return jsonify(result)

        # Fallback to broker manager
        result = broker_mgr.get_live_prices()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/live-stream")
def live_stream():
    """
    Server-Sent Events (SSE) stream for live price updates.
    Pushes NIFTY/BANKNIFTY/SENSEX prices every 3 seconds.
    Connect from frontend: new EventSource('/api/live-stream')
    """
    import time

    def generate():
        while True:
            try:
                data = nse_live.get_live_prices()
                if "error" not in data:
                    yield f"data: {json.dumps(data)}\n\n"
                else:
                    fallback = broker_mgr.get_live_prices()
                    yield f"data: {json.dumps(fallback)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            time.sleep(3)

    from flask import Response
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    })


@app.route("/api/broker-status")
def broker_status():
    """Check which broker is active and configured."""
    try:
        return jsonify(broker_mgr.get_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/quantedge/<symbol>")
def quantedge_signals(symbol: str):
    """
    QuantEdge Option Trading signals.
    Black-Scholes ATM pricing, Greeks, PCR strategy, full option chain.
    """
    try:
        symbol = symbol.upper()
        df = data_collector.get_stock_data(symbol, period="3mo")
        spot = float(df["close"].iloc[-1])
        signals = quantedge.generate_signals(spot, symbol, df)
        return safe_jsonify(signals)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/option-chain/<symbol>")
def option_chain(symbol: str):
    """Get full option chain with CE/PE prices for 11 strikes."""
    try:
        symbol = symbol.upper()
        df = data_collector.get_stock_data(symbol, period="3mo")
        spot = float(df["close"].iloc[-1])
        chain = quantedge.get_full_chain(spot, symbol, df)
        return safe_jsonify(chain)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/prob-strategy/<symbol>")
def prob_strategy(symbol: str):
    """
    Intraday probability & option selling strategy.
    Calculates up/down/flat probability and recommends selling strategy.
    """
    try:
        import math as _m
        symbol = symbol.upper()
        df = data_collector.get_stock_data(symbol, period="6mo")
        spot = round(float(df["close"].iloc[-1]), 2)

        import ta as ta_lib
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # Calculate indicators
        rsi = float(ta_lib.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1])
        macd_ind = ta_lib.trend.MACD(close=close)
        macd_hist = float(macd_ind.macd_diff().iloc[-1])
        atr = float(ta_lib.volatility.AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range().iloc[-1])
        ema_9 = float(ta_lib.trend.EMAIndicator(close=close, window=9).ema_indicator().iloc[-1])
        ema_21 = float(ta_lib.trend.EMAIndicator(close=close, window=21).ema_indicator().iloc[-1])
        adx_ind = ta_lib.trend.ADXIndicator(high=high, low=low, close=close, window=14)
        adx = float(adx_ind.adx().iloc[-1])

        # Historical volatility
        returns = close.pct_change().dropna()
        hv = float(returns.tail(20).std() * _m.sqrt(252))
        iv_est = round(hv * 100, 1)

        # Probability calculation
        bull_score = 0
        bear_score = 0

        if rsi > 55: bull_score += 20
        elif rsi < 45: bear_score += 20
        if macd_hist > 0: bull_score += 15
        else: bear_score += 15
        if ema_9 > ema_21: bull_score += 20
        else: bear_score += 20
        if adx > 25: 
            if float(adx_ind.adx_pos().iloc[-1]) > float(adx_ind.adx_neg().iloc[-1]):
                bull_score += 15
            else:
                bear_score += 15

        # Recent momentum
        ret_1d = float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100)
        if ret_1d > 0.3: bull_score += 15
        elif ret_1d < -0.3: bear_score += 15

        total = bull_score + bear_score
        if total == 0: total = 1
        up_prob = round(bull_score / total * 100, 1)
        down_prob = round(bear_score / total * 100, 1)
        flat_prob = round(max(0, 100 - up_prob - down_prob + 15), 1)  # Some overlap for flat

        # Normalize
        total_p = up_prob + down_prob + flat_prob
        up_prob = round(up_prob / total_p * 100, 1)
        down_prob = round(down_prob / total_p * 100, 1)
        flat_prob = round(100 - up_prob - down_prob, 1)

        # Option selling strategy
        config = {"NIFTY": 50, "BANKNIFTY": 100, "SENSEX": 100}.get(symbol, 50)
        atm = round(spot / config) * config
        expected_range = round(atr * 1.2, 0)

        # Strategy recommendation
        if up_prob > 55:
            strategy = "SELL PUT"
            sell_strike = atm - config * 2  # OTM put
            reason = "Market bias bullish — sell OTM puts to collect premium"
            risk = "Risk if sudden selloff below " + str(sell_strike)
        elif down_prob > 55:
            strategy = "SELL CALL"
            sell_strike = atm + config * 2  # OTM call
            reason = "Market bias bearish — sell OTM calls to collect premium"
            risk = "Risk if sudden rally above " + str(sell_strike)
        else:
            strategy = "SELL BOTH (Iron Condor)"
            sell_strike = atm
            reason = "Market likely range-bound — sell both OTM CE and PE"
            risk = "Risk if breakout in either direction beyond range"

        # Premium estimates using Black-Scholes
        T = 5 / 365  # ~5 days to expiry
        r = 0.065
        ce_strike = atm + config * 2
        pe_strike = atm - config * 2
        ce_premium = quantedge.black_scholes_call(spot, ce_strike, T, r, hv)
        pe_premium = quantedge.black_scholes_put(spot, pe_strike, T, r, hv)

        # Expected return
        if strategy == "SELL PUT":
            exp_return = round(pe_premium / spot * 100, 3)
        elif strategy == "SELL CALL":
            exp_return = round(ce_premium / spot * 100, 3)
        else:
            exp_return = round((ce_premium + pe_premium) / spot * 100, 3)

        result = {
            "symbol": symbol,
            "spot_price": spot,
            "timestamp": datetime.now().isoformat(),
            "probability": {
                "upside": up_prob,
                "downside": down_prob,
                "flat": flat_prob,
            },
            "indicators": {
                "rsi": round(rsi, 1),
                "macd": "Bullish" if macd_hist > 0 else "Bearish",
                "ema_trend": "Bullish" if ema_9 > ema_21 else "Bearish",
                "adx": round(adx, 1),
                "atr": round(atr, 1),
                "iv_estimate": iv_est,
                "1d_return": round(ret_1d, 2),
            },
            "strategy": {
                "recommendation": strategy,
                "reason": reason,
                "risk": risk,
                "expected_range": f"₹{round(spot - expected_range)} — ₹{round(spot + expected_range)}",
            },
            "option_selling": {
                "sell_ce": {
                    "strike": ce_strike,
                    "premium": round(ce_premium, 2),
                    "probability_otm": round(100 - up_prob, 1),
                },
                "sell_pe": {
                    "strike": pe_strike,
                    "premium": round(pe_premium, 2),
                    "probability_otm": round(100 - down_prob, 1),
                },
                "expected_return_pct": exp_return,
                "risk_level": "High" if iv_est > 18 else "Medium" if iv_est > 12 else "Low",
            },
            "actionable_summary": {
                "action": strategy,
                "ce_strike": ce_strike,
                "ce_premium": round(ce_premium, 2),
                "pe_strike": pe_strike,
                "pe_premium": round(pe_premium, 2),
                "max_profit": round(ce_premium + pe_premium, 2) if "BOTH" in strategy else round(ce_premium if "CALL" in strategy else pe_premium, 2),
            },
        }
        return safe_jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Chatbot endpoint for conversational stock analysis and recommendations.

    Request JSON:
        {"message": "Should I buy RELIANCE?"}


    Returns:
        {"reply": "...", "data": {...} or null}
    """
    data = request.get_json()
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"reply": "Please type a message to get started.", "data": None})

    reply, analysis_data = _process_chat_message(message)
    return jsonify({"reply": reply, "data": analysis_data})


def _process_chat_message(message: str) -> tuple:
    """
    Process a chat message and return a response with optional analysis data.

    Args:
        message: User's chat message

    Returns:
        Tuple of (reply_text, analysis_data_or_none)
    """
    msg_lower = message.lower()

    # Greeting patterns
    if any(greet in msg_lower for greet in ["hello", "hi", "hey", "good morning", "good evening"]):
        return (
            "Hello! I'm the Ecloud-Trade assistant. I can help you with:\n"
            "• Stock analysis & recommendations (e.g., \"Analyze RELIANCE\")\n"
            "• Trading signals (e.g., \"Should I buy TCS?\")\n"
            "• Technical indicators (e.g., \"What's the RSI of INFY?\")\n"
            "• USA news & President updates (e.g., \"USA news\")\n"
            "• Options with US impact (e.g., \"Options NIFTY\")\n"
            "• Market overview (e.g., \"How is the market today?\")\n\n"
            "Just type a stock symbol or ask a question!",
            None,
        )

    # Help patterns
    if any(word in msg_lower for word in ["help", "what can you do", "commands"]):
        return (
            "Here's what I can help with:\n\n"
            "📊 **Analyze a stock**: \"Analyze RELIANCE\" or \"Tell me about TCS\"\n"
            "💡 **Get recommendation**: \"Should I buy INFY?\" or \"Is HDFCBANK a good buy?\"\n"
            "📈 **Technical info**: \"RSI of SBIN\" or \"Indicators for WIPRO\"\n"
            "🎯 **Price targets**: \"Target price for TATAMOTORS\"\n"
            "📰 **Sentiment**: \"News sentiment for ADANIENT\"\n"
            "🇺🇸 **USA News**: \"USA news\" or \"US President\" or \"US markets\"\n"
            "📊 **Options**: \"Options NIFTY\" or \"BANKNIFTY options with USA\"\n"
            f"📋 **Available stocks**: {', '.join(SAMPLE_STOCKS)}\n\n"
            "You can also type any NSE stock symbol directly!",
            None,
        )

    # List stocks
    if any(word in msg_lower for word in ["list stocks", "available stocks", "which stocks", "stock list"]):
        return (
            f"Here are the available sample stocks:\n\n"
            + "\n".join(f"• {s}" for s in SAMPLE_STOCKS)
            + "\n\nYou can also enter any NSE-listed stock symbol for analysis.",
            None,
        )

    # Best trade today / Live trade
    if any(phrase in msg_lower for phrase in ["best trade", "best option", "which trade", "what to trade",
                                              "trade today", "which index", "best index",
                                              "live trade", "current trade", "current entry",
                                              "entry trade", "what should i trade"]):
        try:
            import ta as ta_lib

            indices = ["NIFTY", "BANKNIFTY", "SENSEX"]
            results = []

            for idx in indices:
                try:
                    df = data_collector.get_stock_data(idx, period="6mo")
                    if df.empty or len(df) < 30:
                        continue
                    current_price = df["close"].iloc[-1]

                    # Indicators
                    rsi = ta_lib.momentum.RSIIndicator(close=df["close"], window=14).rsi().iloc[-1]
                    macd_ind = ta_lib.trend.MACD(close=df["close"])
                    macd_val = macd_ind.macd().iloc[-1]
                    macd_sig = macd_ind.macd_signal().iloc[-1]
                    atr = ta_lib.volatility.AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14).average_true_range().iloc[-1]

                    # Pivots
                    prev_h, prev_l, prev_c = df["high"].iloc[-2], df["low"].iloc[-2], df["close"].iloc[-2]
                    pivot = (prev_h + prev_l + prev_c) / 3
                    r1 = 2 * pivot - prev_l
                    s1 = 2 * pivot - prev_h

                    # Score
                    score = 0
                    direction = "CE"
                    if rsi > 55: score += 15
                    elif rsi < 45: score -= 15
                    if macd_val > macd_sig: score += 20
                    else: score -= 20
                    if current_price > pivot: score += 15
                    else: score -= 15

                    if score < 0:
                        direction = "PE"

                    step = 100 if idx == "BANKNIFTY" else 50
                    strike = round(current_price / step) * step
                    expected_points = round(atr * 1.5, 0)
                    confidence = min(95, max(30, 50 + abs(score)))

                    if direction == "CE":
                        entry = round(current_price + 20, 0)
                        sl = round(s1, 0)
                        target = round(r1, 0)
                    else:
                        entry = round(current_price - 20, 0)
                        sl = round(r1, 0)
                        target = round(s1, 0)

                    results.append({
                        "index": idx, "price": round(current_price, 2),
                        "direction": f"BUY {direction}", "strike": f"{strike} {direction}",
                        "entry": entry, "sl": sl, "target": target,
                        "confidence": confidence, "score": abs(score),
                        "expected_points": expected_points, "rsi": round(rsi, 1),
                    })
                except Exception:
                    continue

            results.sort(key=lambda x: x["score"], reverse=True)

            if not results:
                return "Could not fetch index data right now. Try again.", None

            best = results[0]
            response = f"🏆 **Best Trade Today: {best['index']}**\n\n"
            response += f"Direction: **{best['direction']}**\n"
            response += f"Strike: {best['strike']}\n"
            response += f"Entry: {best['entry']} | SL: {best['sl']} | Target: {best['target']}\n"
            response += f"Expected Points: +{best['expected_points']}\n"
            response += f"Confidence: {best['confidence']}% | RSI: {best['rsi']}\n\n"

            response += "📊 **All Index Rankings:**\n"
            for r in results:
                response += f"• {r['index']} ₹{r['price']:,.2f} → {r['direction']} | Strike: {r['strike']} | Score: {r['score']}, Conf: {r['confidence']}%\n"

            response += "\n⚠️ Not financial advice. Use proper risk management."
            return response, None
        except Exception as e:
            return f"Error calculating best trade: {str(e)}", None

    # USA News / President / US Markets
    if any(word in msg_lower for word in ["usa", "us news", "us president", "president", "trump", "biden",
                                           "federal reserve", "fed rate", "us market", "wall street",
                                           "s&p", "nasdaq", "dow jones", "vix"]):
        try:
            usa_data = usa_news_analyzer.get_complete_usa_analysis()
            _usa_news_cache["latest"] = usa_data

            response = "🇺🇸 **USA News & Market Impact**\n\n"

            # President news
            pres = usa_data["president_news"]
            response += f"🏛️ **President News**: {pres['sentiment']} (Score: {pres['score']:.3f})\n"
            response += f"Impact: {pres['market_impact']}\n\n"

            # US Markets
            markets = usa_data["us_markets"]
            if "indices" in markets:
                response += "📈 **US Market Indices**:\n"
                for name, data in markets["indices"].items():
                    if isinstance(data, dict) and "change_pct" in data:
                        arrow = "↑" if data["change_pct"] > 0 else "↓"
                        response += f"• {name}: {data['value']:,.2f} ({arrow}{data['change_pct']:+.2f}%)\n"
                response += f"\nUS Mood: {markets.get('us_market_mood', 'N/A')}"
                response += f" | Fear Index: {markets.get('fear_index', 'N/A')}\n\n"

            # Top headlines
            news = usa_data["usa_news"]
            if news.get("top_headlines"):
                response += "📰 **Top Headlines**:\n"
                for h in news["top_headlines"][:4]:
                    response += f"• {h}\n"
                response += "\n"

            # Impact & recommendation
            response += f"🎯 **India Impact**: {usa_data['combined_impact']}\n"
            response += f"📊 **Options Bias**: {usa_data['options_bias']}\n\n"
            response += f"💡 {usa_data['recommendation']}"

            return response, None
        except Exception as e:
            return f"Sorry, I couldn't fetch USA news right now: {str(e)}", None

    # Options analysis
    if any(word in msg_lower for word in ["option", "options", "ce", "pe", "call", "put",
                                           "trade sensex", "trade nifty", "trade banknifty"]):
        index = "NIFTY"
        if "banknifty" in msg_lower or "bank nifty" in msg_lower:
            index = "BANKNIFTY"
        elif "sensex" in msg_lower:
            index = "SENSEX"

        try:
            options_result = options_analyzer.analyze_index_options(index)
            rec = options_result.get("recommendation", {})

            # Also get candlestick patterns and breakout for comprehensive analysis
            try:
                df = data_collector.get_stock_data(index, period="3mo")
                detector = CandlestickPatternDetector(df)
                patterns = detector.detect_all()
                bp = breakout_calc.calculate(df)
            except Exception:
                patterns = []
                bp = {}

            response = f"📊 **{index} Options Analysis**\n\n"
            response += f"Current: ₹{options_result['current_price']:,.2f}\n"
            response += f"Signal: **{rec.get('action', 'N/A')}** (Confidence: {rec.get('confidence', 'N/A')})\n"
            response += f"Score: {rec.get('score', 0)}/10\n\n"
            response += f"🎯 Strike: {rec.get('suggested_strike', 'N/A')} {rec.get('side', '')}\n"
            response += f"Target: {rec.get('target_level', 'N/A')} | SL: {rec.get('stoploss_level', 'N/A')}\n"
            response += f"Risk:Reward: {rec.get('risk_reward', 'N/A')} | Size: {rec.get('position_sizing', 'N/A')}\n\n"

            # Breakout info
            if bp:
                response += f"🚀 Breakout Probability: {bp.get('breakout_probability', 0)}%\n"
                response += f"Upside: {bp.get('upside_probability', 0)}% | Downside: {bp.get('downside_probability', 0)}%\n\n"

            # Candlestick patterns
            if patterns:
                response += "🕯️ **Patterns Detected:**\n"
                for p in patterns[:3]:
                    response += f"• {p['pattern']} → {p['signal']} ({p['confidence']}%)\n"
                response += "\n"

            # USA impact
            if "latest" in _usa_news_cache:
                usa = _usa_news_cache["latest"]
                response += f"🇺🇸 USA Bias: {usa.get('options_bias', 'N/A')}\n"
                response += f"US Impact: {usa.get('combined_impact', 'N/A')}\n\n"

            if rec.get("reasons"):
                response += "**Reasons:**\n"
                for r in rec["reasons"][:5]:
                    response += f"• {r}\n"

            response += "\n⚠️ Not financial advice. Use stop loss."
            return response, None
        except Exception as e:
            return f"Error analyzing {index} options: {str(e)}", None

    # Market overview
    if any(word in msg_lower for word in ["market today", "market overview", "how is market", "nifty"]):
        return (
            "Let me check the market context for you. "
            "Try analyzing a specific stock (e.g., \"Analyze RELIANCE\") "
            "to get the full market context including NIFTY trend and market mood.",
            None,
        )

    # Extract stock symbol from message
    symbol = _extract_symbol(message)

    if not symbol:
        return (
            "I couldn't identify a stock symbol in your message. "
            f"Please mention a valid NSE stock symbol like: {', '.join(SAMPLE_STOCKS[:5])}.\n\n"
            "Examples:\n"
            "• \"Analyze RELIANCE\"\n"
            "• \"Should I buy TCS?\"\n"
            "• \"What's the target for INFY?\"",
            None,
        )

    # Perform analysis
    try:
        # Use cached result if available and recent
        if symbol in _chat_analysis_cache:
            result = _chat_analysis_cache[symbol]
        else:
            result = analyzer.analyze(symbol, train_model=False)
            _chat_analysis_cache[symbol] = result

        # Determine what kind of response to give based on the question
        reply = _format_chat_response(message, result)
        return reply, result

    except ValueError as e:
        return f"Sorry, I couldn't find data for '{symbol}'. Please check if it's a valid NSE stock symbol.", None
    except Exception as e:
        return f"I encountered an error analyzing {symbol}: {str(e)}. Please try again.", None


def _extract_symbol(message: str) -> str:
    """
    Extract a stock symbol from a chat message.

    Args:
        message: User's message

    Returns:
        Extracted symbol or empty string
    """
    msg_upper = message.upper()

    # Check if any known sample stock is mentioned
    for stock in SAMPLE_STOCKS:
        if stock in msg_upper:
            return stock

    # Try to find a capitalized word that looks like a stock symbol (3-15 chars, all caps)
    words = msg_upper.split()
    for word in words:
        # Clean punctuation
        clean = re.sub(r"[^A-Z]", "", word)
        if 3 <= len(clean) <= 15 and clean.isalpha():
            # Skip common English words
            skip_words = {
                "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL",
                "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "BUY", "SELL",
                "HOW", "WHAT", "WHEN", "WHY", "WHO", "SHOULD", "WILL",
                "TELL", "ABOUT", "GIVE", "SHOW", "GET", "STOCK", "PRICE",
                "TARGET", "STOP", "LOSS", "MARKET", "TODAY", "GOOD",
                "ANALYZE", "ANALYSIS", "RECOMMENDATION", "NEWS", "RSI",
                "MACD", "INDICATORS", "TECHNICAL", "SENTIMENT",
                "BEST", "TRADE", "OPTION", "OPTIONS", "INDEX", "WHICH",
                "CALL", "PUT", "NIFTY", "BANKNIFTY", "SENSEX",
            }
            if clean not in skip_words:
                return clean

    return ""


def _format_chat_response(message: str, result: dict) -> str:
    """
    Format a conversational response based on the analysis result and user question.

    Args:
        message: Original user message
        result: Analysis result dictionary

    Returns:
        Formatted response string
    """
    msg_lower = message.lower()
    symbol = result["symbol"]
    rec = result["recommendation"]
    price = result["current_price"]
    trend = result["trend_analysis"]
    risk = result["risk_level"]

    # Recommendation / buy-sell question
    if any(word in msg_lower for word in ["should i buy", "should i sell", "recommend", "suggestion", "buy or sell"]):
        response = f"📊 **{symbol} Recommendation: {rec}**\n\n"
        response += f"Current Price: ₹{price}\n"
        response += f"Trend: {trend} | Risk: {risk}\n\n"
        response += f"🎯 Entry: ₹{result['entry_price']} | Stop Loss: ₹{result['stop_loss']} | Target: ₹{result['target_price']}\n\n"
        response += f"💡 {result['reasoning']}\n\n"
        response += "⚠️ This is not financial advice. Always do your own research."
        return response

    # Technical indicators
    if any(word in msg_lower for word in ["rsi", "macd", "indicator", "technical", "adx", "bollinger"]):
        ti = result["technical_indicators"]
        response = f"📈 **Technical Indicators for {symbol}**\n\n"
        response += f"• RSI: {ti['rsi']} ({ti['rsi_signal']})\n"
        response += f"• MACD: {ti['macd_signal']}\n"
        response += f"• Moving Avg: {ti['ma_signal']}\n"
        response += f"• ADX: {ti['adx']} ({ti['trend_strength']})\n"
        response += f"• Bollinger: {ti['bb_signal']}\n"
        response += f"• Volume Ratio: {ti['volume_ratio']}x\n"
        return response

    # Target / price levels
    if any(word in msg_lower for word in ["target", "stop loss", "entry", "level", "support", "resistance"]):
        sr = result["support_resistance"]
        response = f"🎯 **Price Levels for {symbol}** (CMP: ₹{price})\n\n"
        response += f"Trading Levels:\n"
        response += f"• Entry: ₹{result['entry_price']}\n"
        response += f"• Stop Loss: ₹{result['stop_loss']}\n"
        response += f"• Target: ₹{result['target_price']}\n\n"
        response += f"Support & Resistance:\n"
        response += f"• R2: ₹{sr['resistance_2']} | R1: ₹{sr['resistance_1']}\n"
        response += f"• Pivot: ₹{sr['pivot']}\n"
        response += f"• S1: ₹{sr['support_1']} | S2: ₹{sr['support_2']}\n"
        return response

    # News / sentiment
    if any(word in msg_lower for word in ["news", "sentiment", "headlines"]):
        ns = result["news_sentiment"]
        response = f"📰 **News Sentiment for {symbol}**\n\n"
        response += f"Overall: {ns['overall_sentiment']} (Score: {ns['sentiment_score']:.4f})\n"
        response += f"Positive News: {ns['positive_news']} | Negative: {ns['negative_news']}\n\n"
        if ns.get("top_headlines"):
            response += "Recent Headlines:\n"
            for h in ns["top_headlines"][:3]:
                response += f"• {h}\n"
        return response

    # Prediction
    if any(word in msg_lower for word in ["predict", "forecast", "tomorrow", "week", "month"]):
        preds = result["predictions"]
        response = f"🤖 **ML Predictions for {symbol}**\n\n"
        for period, pred in preds.items():
            label = period.replace("_", " ").title()
            prob = pred["probability_up"] * 100
            arrow = "↑" if pred["direction"] == "UP" else "↓"
            response += f"• {label}: {arrow} {pred['direction']} ({prob:.1f}% probability)\n"
        response += f"\nConfidence based on XGBoost (60%) + Random Forest (40%) ensemble."
        return response

    # Default: full summary
    response = f"📊 **{symbol} Analysis Summary**\n\n"
    response += f"Price: ₹{price} | Trend: {trend}\n"
    response += f"Signal: **{rec}** | Risk: {risk}\n\n"
    response += f"🎯 Entry: ₹{result['entry_price']} | SL: ₹{result['stop_loss']} | Target: ₹{result['target_price']}\n\n"

    preds = result["predictions"]
    response += "🤖 Predictions:\n"
    for period, pred in preds.items():
        label = period.replace("_", " ").title()
        prob = pred["probability_up"] * 100
        response += f"• {label}: {pred['direction']} ({prob:.1f}%)\n"

    response += f"\n📰 Sentiment: {result['news_sentiment']['overall_sentiment']}\n"
    response += f"\n💡 {result['reasoning']}"
    return response


@app.route("/api/stock-signal/<symbol>")
def stock_signal(symbol: str):
    """Quick technical signal for a single stock."""
    try:
        symbol = symbol.upper()
        df = data_collector.get_stock_data(symbol, period="3mo")
        import ta as ta_lib
        close = df["close"]
        price = round(float(close.iloc[-1]), 2)
        rsi = float(ta_lib.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1])
        macd_ind = ta_lib.trend.MACD(close=close)
        macd_hist = float(macd_ind.macd_diff().iloc[-1])
        ema_9 = float(ta_lib.trend.EMAIndicator(close=close, window=9).ema_indicator().iloc[-1])
        ema_21 = float(ta_lib.trend.EMAIndicator(close=close, window=21).ema_indicator().iloc[-1])
        atr = float(ta_lib.volatility.AverageTrueRange(high=df["high"], low=df["low"], close=close, window=14).average_true_range().iloc[-1])

        # Signal
        score = 0
        if rsi > 55: score += 1
        elif rsi < 45: score -= 1
        if macd_hist > 0: score += 1
        else: score -= 1
        if ema_9 > ema_21: score += 1
        else: score -= 1

        signal = "BUY" if score >= 2 else "SELL" if score <= -2 else "HOLD"
        entry = round(price, 2)
        sl = round(price - atr * 1.5, 2) if signal == "BUY" else round(price + atr * 1.5, 2)
        t1 = round(price + atr * 1.0, 2) if signal == "BUY" else round(price - atr * 1.0, 2)
        t2 = round(price + atr * 2.0, 2) if signal == "BUY" else round(price - atr * 2.0, 2)

        return safe_jsonify({
            "symbol": symbol, "price": price, "signal": signal,
            "rsi": round(rsi, 1), "macd": "Bullish" if macd_hist > 0 else "Bearish",
            "ema": "Bullish" if ema_9 > ema_21 else "Bearish",
            "entry": entry, "stop_loss": sl, "target_1": t1, "target_2": t2,
            "atr": round(atr, 2),
            "change_pct": round(float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100), 2),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── WebSocket Events ───────────────────────────────────────────────────────────
import threading
import time as _time

_ws_streaming = False

def _stream_live_data():
    """Background thread that pushes live prices via WebSocket every 3 seconds."""
    global _ws_streaming
    _ws_streaming = True
    while _ws_streaming:
        try:
            data = nse_live.get_live_prices()
            if "error" not in data:
                socketio.emit('live_prices', _sanitize_for_json(data), namespace='/')
        except Exception:
            pass
        _time.sleep(3)


@socketio.on('connect')
def handle_connect():
    """Client connected — start streaming if not already."""
    global _ws_streaming
    if not _ws_streaming:
        thread = threading.Thread(target=_stream_live_data, daemon=True)
        thread.start()
    # Send immediate data
    try:
        data = nse_live.get_live_prices()
        if "error" not in data:
            emit('live_prices', _sanitize_for_json(data))
    except Exception:
        pass


@socketio.on('disconnect')
def handle_disconnect():
    pass


@socketio.on('request_data')
def handle_request_data(msg):
    """Client requests specific data (two-way communication)."""
    action = msg.get('action', '')
    symbol = msg.get('symbol', 'NIFTY')

    if action == 'live_prices':
        data = nse_live.get_live_prices()
        emit('live_prices', _sanitize_for_json(data))

    elif action == 'buy_sell_signals':
        # Fetch signals for all 3 indices
        results = {}
        for idx in ['NIFTY', 'BANKNIFTY', 'SENSEX']:
            try:
                import ta as ta_lib
                df = data_collector.get_stock_data(idx, period="6mo")
                current_price = float(df["close"].iloc[-1])
                prev_h = float(df["high"].iloc[-2])
                prev_l = float(df["low"].iloc[-2])
                prev_c = float(df["close"].iloc[-2])
                pivot = (prev_h + prev_l + prev_c) / 3
                r1 = 2 * pivot - prev_l
                s1 = 2 * pivot - prev_h
                pivots = {"pivot": round(pivot, 2), "r1": round(r1, 2), "s1": round(s1, 2)}
                rsi = float(ta_lib.momentum.RSIIndicator(close=df["close"], window=14).rsi().iloc[-1])
                macd_ind = ta_lib.trend.MACD(close=df["close"])
                macd_val = float(macd_ind.macd().iloc[-1])
                macd_sig = float(macd_ind.macd_signal().iloc[-1])
                ema_9 = float(ta_lib.trend.EMAIndicator(close=df["close"], window=9).ema_indicator().iloc[-1])
                ema_21 = float(ta_lib.trend.EMAIndicator(close=df["close"], window=21).ema_indicator().iloc[-1])
                vol_sma = float(df["volume"].rolling(20).mean().iloc[-1])
                vol_ratio = float(df["volume"].iloc[-1]) / vol_sma if vol_sma > 0 else 1
                indicators = {"rsi": round(rsi, 2), "macd_crossover": "Bullish" if macd_val > macd_sig else "Bearish", "volume_ratio": round(vol_ratio, 2), "ema_9": round(ema_9, 2), "ema_21": round(ema_21, 2)}
                signal = intraday_gen.generate_option_intraday(idx, current_price, pivots, indicators)
                signal["indicators"] = indicators
                step = 100 if idx == "BANKNIFTY" else 50
                signal["atm_strike"] = round(current_price / step) * step
                results[idx] = signal
            except Exception as e:
                results[idx] = {"error": str(e)}
        emit('buy_sell_data', _sanitize_for_json(results))

    elif action == 'intraday_signal':
        try:
            import ta as ta_lib
            df = data_collector.get_stock_data(symbol, period="6mo")
            current_price = float(df["close"].iloc[-1])
            prev_h = float(df["high"].iloc[-2])
            prev_l = float(df["low"].iloc[-2])
            prev_c = float(df["close"].iloc[-2])
            pivot = (prev_h + prev_l + prev_c) / 3
            r1 = 2 * pivot - prev_l
            s1 = 2 * pivot - prev_h
            pivots = {"pivot": round(pivot, 2), "r1": round(r1, 2), "s1": round(s1, 2)}
            rsi = float(ta_lib.momentum.RSIIndicator(close=df["close"], window=14).rsi().iloc[-1])
            macd_ind = ta_lib.trend.MACD(close=df["close"])
            macd_val = float(macd_ind.macd().iloc[-1])
            macd_sig = float(macd_ind.macd_signal().iloc[-1])
            indicators = {"rsi": round(rsi, 2), "macd_crossover": "Bullish" if macd_val > macd_sig else "Bearish"}
            signal = intraday_gen.generate_option_intraday(symbol, current_price, pivots, indicators)
            emit('signal_data', _sanitize_for_json(signal))
        except Exception as e:
            emit('signal_data', {"error": str(e)})

    elif action == 'quantedge':
        try:
            df = data_collector.get_stock_data(symbol, period="3mo")
            spot = float(df["close"].iloc[-1])
            signals = quantedge.generate_signals(spot, symbol, df)
            emit('quantedge_data', _sanitize_for_json(signals))
        except Exception as e:
            emit('quantedge_data', {"error": str(e)})


if __name__ == "__main__":
    socketio.run(app, debug=FLASK_DEBUG, port=FLASK_PORT, host="0.0.0.0", allow_unsafe_werkzeug=True)
