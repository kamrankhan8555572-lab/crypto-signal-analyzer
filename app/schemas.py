from pydantic import BaseModel
from typing import List, Optional, Any


class AnalyzeRequest(BaseModel):
    symbol: str = "BTC-USD"
    periods: int = 200
    seed: str = "demo"
    freq: str = "1min"


class IndicatorEntry(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class SignalReason(BaseModel):
    indicator: str
    description: str
    passed: bool


class AnalyzeResponse(BaseModel):
    symbol: str
    mode: str
    signal: str
    confidence: str
    reasons: List[SignalReason]
    risk_score: float
    invalidation_price: Optional[float]
    latest: IndicatorEntry
    debug: Optional[Any]
