import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = BASE_DIR / "scripts"

DATA_FILES = {
    "daily": DATA_DIR / "tickers_ohlcv.csv",
    "hourly": DATA_DIR / "tickers_1h_ohlcv.csv",
    "30min": DATA_DIR / "tickers_30m_ohlcv.csv",
    "15min": DATA_DIR / "tickers_15m_ohlcv.csv",
    "5min": DATA_DIR / "tickers_5m_ohlcv.csv",
    "spy": DATA_DIR / "SPY_ohlcv.csv",
    "gold": DATA_DIR / "gold_daily.csv",
}

REFRESH_THRESHOLD_HOURS = 4
MAX_RECOMMENDATIONS = 50
DEFAULT_LOOKBACK_DAYS = 252

PRICE_RANGES = {
    "penny": (0, 5),
    "low": (5, 20),
    "mid": (20, 100),
    "high": (100, float("inf")),
}

STRATEGY_WEIGHTS = {
    "ELITE": 1.3,
    "HIGH": 1.1,
    "MEDIUM": 1.0,
}

STOP_LOSS_PCT = {
    "aggressive": 0.05,
    "standard": 0.07,
    "conservative": 0.10,
}
