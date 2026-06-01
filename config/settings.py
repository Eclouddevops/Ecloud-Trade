"""
Application configuration settings.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Data Source Settings ───────────────────────────────────────────────────────
YFINANCE_SUFFIX = ".NS"  # NSE suffix for yfinance
HISTORICAL_PERIOD = "2y"  # Default historical data period
INTERVAL = "1d"  # Default data interval

# ─── Technical Indicator Parameters ────────────────────────────────────────────
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
EMA_SHORT = 20
EMA_LONG = 50
SMA_200 = 200
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2
ATR_PERIOD = 14

# ─── ML Model Settings ─────────────────────────────────────────────────────────
TRAIN_TEST_SPLIT = 0.8
RANDOM_STATE = 42
XGBOOST_PARAMS = {
    "n_estimators": 200,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
}
RANDOM_FOREST_PARAMS = {
    "n_estimators": 200,
    "max_depth": 10,
    "random_state": 42,
}

# ─── Prediction Horizons ───────────────────────────────────────────────────────
PREDICTION_HORIZONS = {
    "1_day": 1,
    "1_week": 5,
    "1_month": 22,
}

# ─── Risk Management ──────────────────────────────────────────────────────────
STOP_LOSS_MULTIPLIER = 1.5  # ATR multiplier for stop loss
TARGET_RISK_REWARD = 2.0  # Risk-reward ratio for target

# ─── Stock Universe ────────────────────────────────────────────────────────────
SAMPLE_STOCKS = [
    "RELIANCE",
    "TCS",
    "INFY",
    "HDFCBANK",
    "ICICIBANK",
    "SBIN",
    "TATAMOTORS",
    "ADANIENT",
    "WIPRO",
    "BAJFINANCE",
]

NIFTY50_SYMBOL = "^NSEI"
SENSEX_SYMBOL = "^BSESN"

# ─── API Keys ──────────────────────────────────────────────────────────────────
BREEZE_API_KEY = os.getenv("BREEZE_API_KEY", "")
BREEZE_SECRET = os.getenv("BREEZE_SECRET", "")

# ─── Flask Settings ────────────────────────────────────────────────────────────
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))

# ─── File Paths ────────────────────────────────────────────────────────────────
MODEL_SAVE_DIR = "models/saved"
DATA_CACHE_DIR = "data/cache"
