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


class OhlcvUploadRequest(BaseModel):
    """Model for user-provided OHLCV JSON payload.

    data: list of IndicatorEntry rows (timestamp, open, high, low, close, volume)
    min_periods: optional minimum required rows before analysis (default 20)
    symbol: optional metadata only
    """
    symbol: Optional[str] = "BTC-USD"
    data: List[IndicatorEntry]
    min_periods: Optional[int] = 20


class SignalReason(BaseModel):
    indicator: str
    description: str
    passed: bool


class RuleResult(BaseModel):
    id: str
    indicator: str
    passed: bool
    value: Optional[float]
    threshold: Optional[Any]
    weight: int
    explanation: str


class AnalyzeResponse(BaseModel):
    symbol: str
    mode: str
    signal: str
    confidence: str
    confidence_score: float
    reasons: List[RuleResult]
    risk_score: float
    invalidation_price: Optional[float]
    latest: IndicatorEntry
    debug: Optional[Any]
