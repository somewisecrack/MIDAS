from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class TriggeredStrategy(BaseModel):
    name: str
    win_rate: str
    max_gain: Optional[str] = None
    signal: str
    priority: str = "MEDIUM"


class Recommendation(BaseModel):
    rank: int
    ticker: str
    stock_price: str
    type: str
    strategies_triggered: List[TriggeredStrategy]
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    holding_period: str
    confidence_score: int = Field(ge=0, le=100)
    reasoning: str
    is_sp500: bool = False


class ScanResponse(BaseModel):
    scan_id: str
    scan_time: datetime
    data_freshness: str
    data_last_updated: Optional[datetime]
    stocks_scanned: int
    sp500_scanned: int = 0
    other_scanned: int = 0
    strategies_run: int
    regime: str
    recommendations: List[Recommendation]


class DataStatus(BaseModel):
    last_updated: Optional[datetime]
    freshness: str
    stocks: int
    is_stale: bool


class StrategyInfo(BaseModel):
    name: str
    type: str
    priority: str
    description: str
    optimal_price_range: str
    win_rate: Optional[str] = None
    profit_factor: Optional[str] = None
