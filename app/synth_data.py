from datetime import datetime, timedelta
import numpy as np
import pandas as pd


def generate_ohlcv(symbol: str = "DEMO", start: str = None, periods: int = 200, seed: str = "demo", freq: str = "1min") -> pd.DataFrame:
    """Deterministic synthetic OHLCV generator.

    - Uses geometric Brownian motion with a seed derived from symbol and seed string.
    - Deterministic for the same inputs.
    - Returns a pandas DataFrame indexed by timestamp with columns: open, high, low, close, volume
    """
    # create deterministic seed
    seed_str = f"{symbol}:{seed}:{periods}:{freq}"
    s = abs(hash(seed_str)) % (2**32)
    rng = np.random.default_rng(s)

    # time index
    if start is None:
        start_dt = datetime(2020, 1, 1)
    else:
        start_dt = pd.to_datetime(start)
    # For simplicity use minutes spacing
    idx = pd.date_range(start=start_dt, periods=periods, freq=freq)

    # price process parameters
    S0 = 100.0 + (abs(hash(symbol)) % 500) / 10.0  # vary by symbol
    mu = 0.0001  # small drift
    sigma = 0.0015 + ((abs(hash(seed)) % 100) / 100000.0)

    # generate returns
    returns = rng.normal(loc=mu, scale=sigma, size=periods)
    prices = S0 * np.exp(np.cumsum(returns))

    # derive OHLC from close prices by adding small random intrabar moves
    opens = np.concatenate([[prices[0]], prices[:-1]])
    highs = np.maximum(opens, prices) * (1 + rng.random(size=periods) * 0.001)
    lows = np.minimum(opens, prices) * (1 - rng.random(size=periods) * 0.001)
    closes = prices

    # volume synthetic but deterministic
    base_vol = 100 + (abs(hash(symbol)) % 1000)
    volume = (base_vol * (1 + 0.1 * rng.standard_normal(size=periods))).astype(int)
    volume = np.maximum(1, volume)

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volume,
    }, index=idx)
    df.index.name = "timestamp"
    return df
