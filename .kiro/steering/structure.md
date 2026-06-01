# Project Structure

```
Ecloud-Trade/
├── main.py                     # CLI entry point — batch stock analysis
├── app.py                      # Flask web app — dashboard + REST API
├── live_dashboard.py           # Real-time streaming dashboard
├── dashboard.py                # Static dashboard generation
├── requirements.txt            # Python dependencies (pinned minimums)
├── .env.example                # Environment variable template
│
├── config/
│   └── settings.py             # All configuration constants and parameters
│
├── data/
│   ├── data_collector.py       # Market data fetching via yfinance
│   ├── news_sentiment.py       # Google News scraping + TextBlob sentiment
│   ├── market_overview.py      # Index data, gainers/losers, sector performance
│   ├── candlestick_patterns.py # Candlestick pattern detection
│   ├── options_analyzer.py     # Options chain analysis
│   └── cache/                  # Runtime cache (JSON analysis results, portfolio state)
│
├── indicators/
│   └── technical.py            # All technical indicator calculations (uses `ta` lib)
│
├── models/
│   ├── feature_engineering.py  # 40+ ML features from price/volume/indicators
│   ├── predictor.py            # XGBoost + Random Forest training and prediction
│   └── saved/                  # Persisted .pkl model files (per stock × horizon)
│
├── analysis/
│   └── analyzer.py             # Main orchestrator — combines all components into final signal
│
├── modules/                    # Extended/enterprise feature modules
│   ├── backtesting.py          # Strategy backtesting
│   ├── breakout_probability.py # Breakout detection
│   ├── broker_integration.py   # Broker API integration (ICICI Breeze)
│   ├── company_fundamentals.py # Fundamental analysis
│   ├── deep_analysis.py        # Extended technical analysis
│   ├── global_market.py        # Global market correlation
│   ├── intraday_signals.py     # Intraday trading signals
│   ├── news_intelligence.py    # Advanced news processing
│   ├── pivot_analysis.py       # Pivot point strategies
│   ├── risk_manager.py         # Position sizing and risk management
│   └── smart_option_picker.py  # Options strategy selection
│
└── templates/
    ├── index.html              # Main Flask dashboard template
    ├── live_dashboard.html     # Live streaming dashboard
    └── dashboard_standalone.html
```

## Architecture Pattern

Pipeline-style data flow with class-based separation of concerns:

1. **Data Layer** (`data/`) — fetches raw market data and news
2. **Indicator Layer** (`indicators/`) — computes technical indicators on DataFrames
3. **Model Layer** (`models/`) — feature engineering + ML training/prediction
4. **Analysis Layer** (`analysis/`) — orchestrates the pipeline and generates final signals
5. **Presentation Layer** (`app.py`, `main.py`, `templates/`) — CLI and web interfaces
6. **Modules** (`modules/`) — optional extended features, loosely coupled

## Key Conventions

- Each layer is a separate package with `__init__.py`
- The `StockAnalyzer` class in `analysis/analyzer.py` is the central orchestrator
- Data flows as pandas DataFrames between layers
- Configuration is imported from `config.settings` — never hardcoded in modules
- Model files follow naming: `{SYMBOL}_{horizon}_{model_type}.pkl`
- Cache files go in `data/cache/`
