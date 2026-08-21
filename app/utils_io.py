from typing import List, Dict, Any
from fastapi import HTTPException
import pandas as pd


def parse_ohlcv_json(data: List[Dict[str, Any]], min_periods: int = 20) -> pd.DataFrame:
    """Validate and normalize a JSON list of OHLCV rows into a pandas DataFrame.

    Expected input: list of dicts with keys: timestamp, open, high, low, close, volume
    - timestamp: ISO string or any timestamp parsable by pandas.to_datetime
    - numeric columns will be coerced to floats/ints and validated
    - index will be set to timestamp and named 'timestamp'
    - enforces at least min_periods rows

    Raises HTTPException(400) for validation errors.
    """
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="data must be a list of rows")

    if len(data) < min_periods:
        raise HTTPException(status_code=400, detail=f"insufficient rows: got {len(data)}, need at least {min_periods}")

    try:
        df = pd.DataFrame(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid data format: {e}")

    expected_cols = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"missing columns: {missing}")

    # parse timestamp
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid timestamp values: {e}")

    df = df.set_index("timestamp")
    df.index.name = "timestamp"

    # coerce numeric columns
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    # check for NaNs in numeric columns
    if df[["open", "high", "low", "close", "volume"]].isnull().any().any():
        raise HTTPException(status_code=400, detail="numeric columns contain non-numeric or missing values")

    # ensure volume is integer
    try:
        df["volume"] = df["volume"].astype(int)
    except Exception:
        # should not happen due to previous check
        raise HTTPException(status_code=400, detail="invalid volume values")

    return df
