"""
Ecloud-Trade: Standalone Dashboard
===================================
Complete Indian Share Market Analysis & Prediction System
Fetches LIVE daily market data and opens a full dashboard in your browser.
No server needed.

Usage:
    python dashboard.py
    python dashboard.py RELIANCE
    python dashboard.py TCS INFY HDFCBANK
"""
import sys
import os
import json
import webbrowser
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analysis.analyzer import StockAnalyzer
from data.market_overview import MarketOverview
from config.settings import SAMPLE_STOCKS


def fetch_market_overview() -> dict:
    """Fetch live daily market data (indices, gainers, losers, sectors)."""
    print("\n[MARKET] Fetching daily market overview...")
    overview = MarketOverview()
    return overview.get_market_summary()


def run_analysis(symbols: list) -> list:
    """Run analysis on all requested stocks."""
    analyzer = StockAnalyzer()
    results = []
    for symbol in symbols:
        try:
            result = analyzer.analyze(symbol, train_model=True)
            results.append(result)
        except Exception as e:
            print(f"  Error analyzing {symbol}: {e}")
            results.append({"symbol": symbol, "error": str(e)})
    return results


def build_dashboard_html(results: list, market_data: dict) -> str:
    """Build the complete HTML dashboard with market overview + stock analysis."""
    results_json = json.dumps(results, default=str)
    market_json = json.dumps(market_data, default=str)
    timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")

    template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "templates", "dashboard_standalone.html"
    )
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("{{RESULTS_DATA}}", results_json)
    html = html.replace("{{MARKET_DATA}}", market_json)
    html = html.replace("{{TIMESTAMP}}", timestamp)

    return html


def main():
    if len(sys.argv) > 1:
        symbols = [s.upper() for s in sys.argv[1:]]
    else:
        symbols = ["RELIANCE", "TCS", "INFY"]

    print("\n" + "=" * 60)
    print("  Ecloud-Trade: Live Market Dashboard")
    print("=" * 60)
    print(f"  Stocks: {', '.join(symbols)}")
    print(f"  Fetching live data & generating dashboard...")
    print("=" * 60)

    # Step 1: Fetch daily market overview
    market_data = fetch_market_overview()
    print(f"\n  Market Status: {market_data['market_status']}")
    nifty = market_data["indices"].get("NIFTY_50", {})
    print(f"  NIFTY 50: {nifty.get('value', 'N/A')} ({nifty.get('change_pct', 0):+.2f}%)")

    # Step 2: Run stock analysis
    results = run_analysis(symbols)

    # Step 3: Generate HTML dashboard
    html_content = build_dashboard_html(results, market_data)

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "dashboard_output.html"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n  Dashboard saved to: {output_path}")
    print("  Opening in browser...")

    webbrowser.open(f"file:///{os.path.abspath(output_path)}")
    print("\n  Done! Check your browser.\n")


if __name__ == "__main__":
    main()
