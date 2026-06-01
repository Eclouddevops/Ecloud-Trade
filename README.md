# Ecloud-Trade: Indian Share Market Analysis & Prediction System

A Python-based quantitative analysis and prediction system for Indian stock market (NSE/BSE). Combines technical analysis, machine learning, and news sentiment to generate actionable trading signals.

## Architecture

```
Live Market Data (Yahoo Finance / NSE)
        ↓
Data Collection (yfinance)
        ↓
Technical Indicators (RSI, MACD, EMA, SMA, Bollinger, ATR, ADX)
        ↓
Feature Engineering (40+ features)
        ↓
ML Models (XGBoost + Random Forest ensemble)
        ↓
News Sentiment Analysis (TextBlob)
        ↓
Trading Signal (BUY / SELL / HOLD)
```

## Features

- **Real-time Data**: Fetches live and historical OHLCV data from NSE via Yahoo Finance
- **Technical Analysis**: RSI, MACD, EMA, SMA, Bollinger Bands, ATR, ADX, Stochastic, OBV
- **ML Predictions**: XGBoost + Random Forest ensemble for 1-day, 1-week, and 1-month forecasts
- **News Sentiment**: Scrapes Google News and performs sentiment analysis
- **Trading Signals**: BUY/SELL/HOLD with entry, stop loss, and target prices
- **Risk Assessment**: ATR-based risk levels and position sizing
- **Web Dashboard**: Flask-based UI for interactive analysis
- **REST API**: JSON endpoints for integration

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run CLI Analysis

```bash
# Analyze single stock
python main.py RELIANCE

# Analyze multiple stocks
python main.py RELIANCE TCS INFY HDFCBANK

# Analyze all sample stocks
python main.py RELIANCE TCS INFY HDFCBANK ICICIBANK SBIN TATAMOTORS ADANIENT
```

### 3. Run Web Dashboard

```bash
python app.py
```

Open http://localhost:5000 in your browser.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/analyze` | POST | Full analysis with ML training |
| `/api/quick-analysis/<symbol>` | GET | Quick analysis (no retraining) |
| `/api/stocks` | GET | List available stocks |
| `/api/health` | GET | Health check |

### Example API Call

```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "RELIANCE", "train": true}'
```

## Output Format (JSON)

```json
{
  "symbol": "RELIANCE",
  "current_price": 2450.50,
  "trend_analysis": "Bullish",
  "recommendation": "BUY",
  "entry_price": 2450.50,
  "stop_loss": 2380.25,
  "target_price": 2590.75,
  "risk_level": "Medium",
  "predictions": {
    "1_day": {"direction": "UP", "probability_up": 0.62},
    "1_week": {"direction": "UP", "probability_up": 0.58},
    "1_month": {"direction": "UP", "probability_up": 0.65}
  },
  "technical_indicators": {...},
  "news_sentiment": {...},
  "reasoning": "..."
}
```

## Project Structure

```
Ecloud-Trade/
├── main.py                  # CLI entry point
├── app.py                   # Flask web application
├── requirements.txt         # Python dependencies
├── config/
│   └── settings.py          # Configuration & parameters
├── data/
│   ├── data_collector.py    # Market data fetching
│   └── news_sentiment.py    # News scraping & sentiment
├── indicators/
│   └── technical.py         # Technical indicator calculations
├── models/
│   ├── feature_engineering.py  # ML feature creation
│   ├── predictor.py         # XGBoost & Random Forest models
│   └── saved/               # Saved model files
├── analysis/
│   └── analyzer.py          # Main analysis engine
└── templates/
    └── index.html           # Web dashboard UI
```

## Technical Indicators Used

| Indicator | Purpose |
|-----------|---------|
| RSI (14) | Overbought/Oversold detection |
| MACD (12,26,9) | Trend reversal signals |
| EMA 20/50 | Short-term trend direction |
| SMA 50/200 | Long-term trend & Golden/Death cross |
| Bollinger Bands | Volatility & mean reversion |
| ATR (14) | Risk management & stop loss |
| ADX | Trend strength measurement |
| Stochastic | Momentum oscillator |
| OBV | Volume confirmation |

## ML Model Details

- **XGBoost**: Primary model (60% weight in ensemble)
- **Random Forest**: Secondary model (40% weight)
- **Features**: 40+ engineered features from price, volume, and indicators
- **Target**: Binary classification (price UP/DOWN)
- **Horizons**: 1 day, 5 days (1 week), 22 days (1 month)

## Supported Stocks

Default test universe: RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, SBIN, TATAMOTORS, ADANIENT, WIPRO, BAJFINANCE

Any NSE-listed stock can be analyzed by entering its symbol.

## Disclaimer

⚠️ **This system is for educational and research purposes only.** It does not constitute financial advice. Stock market investments carry risk. Always do your own research and consult a qualified financial advisor before making investment decisions.

## License

MIT
