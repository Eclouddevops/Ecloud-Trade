"""
Ecloud-Trade: Indian Share Market Analysis & Prediction System
==============================================================

Main entry point for CLI-based stock analysis.
Run this script to analyze stocks from the command line.

Usage:
    python main.py                    # Analyze default stock (RELIANCE)
    python main.py INFY               # Analyze specific stock
    python main.py RELIANCE TCS INFY  # Analyze multiple stocks
"""
import sys
import json
from analysis.analyzer import StockAnalyzer
from config.settings import SAMPLE_STOCKS


def print_analysis(result: dict):
    """Pretty-print analysis results to console."""
    print(f"\n{'='*70}")
    print(f"  STOCK ANALYSIS REPORT: {result['symbol']}")
    print(f"  Generated: {result['analysis_timestamp']}")
    print(f"{'='*70}")

    print(f"\n  Current Price: ₹{result['current_price']}")
    print(f"  Sector: {result['stock_info'].get('sector', 'N/A')}")

    # Signal
    print(f"\n{'─'*70}")
    print(f"  📊 RECOMMENDATION: {result['recommendation']}")
    print(f"  📈 Trend: {result['trend_analysis']}")
    print(f"  ⚠️  Risk Level: {result['risk_level']}")
    print(f"{'─'*70}")

    # Trading Levels
    print(f"\n  💰 Trading Levels:")
    print(f"     Entry Price:  ₹{result['entry_price']}")
    print(f"     Stop Loss:    ₹{result['stop_loss']}")
    print(f"     Target Price: ₹{result['target_price']}")

    # Predictions
    print(f"\n  🤖 ML Predictions:")
    for period, pred in result['predictions'].items():
        direction = pred['direction']
        prob = pred['probability_up'] * 100
        arrow = "↑" if direction == "UP" else "↓"
        print(f"     {period.replace('_', ' ').title()}: {arrow} {direction} ({prob:.1f}% probability)")

    # Technical Summary
    ti = result['technical_indicators']
    print(f"\n  📉 Technical Indicators:")
    print(f"     RSI: {ti['rsi']} ({ti['rsi_signal']})")
    print(f"     MACD: {ti['macd_signal']}")
    print(f"     Moving Avg: {ti['ma_signal']}")
    print(f"     ADX: {ti['adx']} ({ti['trend_strength']})")
    print(f"     Bollinger: {ti['bb_signal']}")

    # Support/Resistance
    sr = result['support_resistance']
    print(f"\n  🎯 Support & Resistance:")
    print(f"     R2: ₹{sr['resistance_2']}  |  R1: ₹{sr['resistance_1']}")
    print(f"     Pivot: ₹{sr['pivot']}")
    print(f"     S1: ₹{sr['support_1']}  |  S2: ₹{sr['support_2']}")

    # News
    ns = result['news_sentiment']
    print(f"\n  📰 News Sentiment: {ns['overall_sentiment']} (Score: {ns['sentiment_score']:.4f})")
    print(f"     Market Mood: {result['market_context']['market_mood']}")
    print(f"     NIFTY Trend: {result['market_context']['nifty_trend']}")

    # Reasoning
    print(f"\n  💡 Reasoning:")
    print(f"     {result['reasoning']}")

    print(f"\n{'='*70}\n")


def main():
    """Main function to run stock analysis."""
    analyzer = StockAnalyzer()

    # Get stocks from command line args or use default
    if len(sys.argv) > 1:
        stocks = [s.upper() for s in sys.argv[1:]]
    else:
        stocks = ["RELIANCE"]

    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + " Ecloud-Trade: Indian Market Analysis & Prediction System ".center(68) + "║")
    print("╚" + "═"*68 + "╝")
    print(f"\nStocks to analyze: {', '.join(stocks)}")
    print(f"Available sample stocks: {', '.join(SAMPLE_STOCKS)}")

    all_results = []

    for symbol in stocks:
        try:
            result = analyzer.analyze(symbol, train_model=True)
            print_analysis(result)
            all_results.append(result)

            # Save individual result as JSON
            with open(f"data/cache/{symbol}_analysis.json", "w") as f:
                json.dump(result, f, indent=2, default=str)
            print(f"  💾 Saved: data/cache/{symbol}_analysis.json")

        except Exception as e:
            print(f"\n  ❌ Error analyzing {symbol}: {e}")

    # Summary
    if len(all_results) > 1:
        print(f"\n{'='*70}")
        print("  SUMMARY")
        print(f"{'='*70}")
        for r in all_results:
            print(f"  {r['symbol']:12s} | {r['recommendation']:12s} | "
                  f"₹{r['current_price']:>10} | Risk: {r['risk_level']}")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
