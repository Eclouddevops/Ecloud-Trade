# Tech Stack

## Language & Runtime

- Python 3.10+
- No build system — standard pip-based workflow

## Key Libraries

| Category | Libraries |
|----------|-----------|
| Data | yfinance, pandas, numpy |
| Technical Analysis | ta (Technical Analysis library) |
| ML | scikit-learn, xgboost, joblib (model persistence) |
| NLP/Sentiment | textblob, beautifulsoup4, requests |
| Web | Flask (backend + templates) |
| Visualization | plotly |
| Config | python-dotenv |

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run CLI analysis (single or multiple stocks)
python main.py RELIANCE
python main.py RELIANCE TCS INFY

# Run web dashboard (serves on http://localhost:5000)
python app.py

# Run live dashboard
python live_dashboard.py
```

## Configuration

- Environment variables loaded from `.env` (see `.env.example`)
- All tunable parameters centralized in `config/settings.py`
- ML hyperparameters, indicator periods, risk multipliers, and Flask settings are all in settings.py

## Code Style Conventions

- Docstrings on all modules, classes, and public methods (Google-style with Args/Returns)
- Type hints on function signatures
- Class-based architecture — each concern is a class (StockAnalyzer, MarketDataCollector, TechnicalIndicators, etc.)
- Lowercase column names for DataFrames (open, high, low, close, volume)
- Constants in UPPER_SNAKE_CASE defined in config/settings.py
- Print statements with emoji prefixes for CLI progress feedback
- JSON-serializable return values from analysis methods
- Models saved as `.pkl` files via joblib
