# Ecloud-Trade

Quantitative analysis and prediction system for the Indian stock market (NSE/BSE). Combines technical analysis, ML-based price prediction, and news sentiment to generate actionable trading signals (BUY/SELL/HOLD) with entry, stop-loss, and target prices.

## Core Capabilities

- Real-time and historical OHLCV data collection from NSE via Yahoo Finance
- Technical indicator calculation (RSI, MACD, EMA, SMA, Bollinger Bands, ATR, ADX, Stochastic, OBV)
- ML ensemble predictions (XGBoost 60% + Random Forest 40%) for 1-day, 1-week, and 1-month horizons
- News sentiment analysis via Google News scraping + TextBlob
- Composite scoring system (-10 to +10) combining technicals, ML, and sentiment
- ATR-based risk management for stop-loss and target calculation
- Flask web dashboard and REST API for interactive analysis
- CLI interface for batch stock analysis

## Target Market

NSE-listed Indian equities. Default universe: RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, SBIN, TATAMOTORS, ADANIENT, WIPRO, BAJFINANCE.

## Disclaimer

Educational and research purposes only. Not financial advice.
