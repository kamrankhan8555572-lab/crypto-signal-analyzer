import pandas as pd
import numpy as np


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=(period - 1), adjust=False).mean()
    ma_down = down.ewm(com=(period - 1), adjust=False).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger_bands(series: pd.Series, period: int = 20, n_std: float = 2.0):
    ma = series.rolling(window=period, min_periods=1).mean()
    std = series.rolling(window=period, min_periods=1).std()
    upper = ma + n_std * std
    lower = ma - n_std * std
    return upper, ma, lower


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=1).mean()
    return atr


def support_resistance(series: pd.Series, window: int = 5):
    # Simple pivot detection: a point is resistance if it's the max in the window, support if min.
    sr = pd.DataFrame(index=series.index)
    sr["support"] = series[(series == series.rolling(window=window, center=True, min_periods=1).min())]
    sr["resistance"] = series[(series == series.rolling(window=window, center=True, min_periods=1).max())]
    # forward fill last known support/resistance
    sr["support_ffill"] = sr["support"].ffill()
    sr["resistance_ffill"] = sr["resistance"].ffill()
    return sr["support_ffill"], sr["resistance_ffill"]


def volatility(series: pd.Series, period: int = 20) -> pd.Series:
    return series.pct_change().rolling(window=period, min_periods=1).std() * (252 ** 0.5)


def attach_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema20"] = ema(df["close"], 20)
    df["ema50"] = ema(df["close"], 50)
    df["ema200"] = ema(df["close"], 200)
    df["rsi14"] = rsi(df["close"], 14)
    macd_line, signal_line, hist = macd(df["close"], 12, 26, 9)
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df["macd_hist"] = hist
    upper, ma20, lower = bollinger_bands(df["close"], 20, 2)
    df["bb_upper"] = upper
    df["bb_mid"] = ma20
    df["bb_lower"] = lower
    df["atr14"] = atr(df, 14)
    df["volatility20"] = volatility(df["close"], 20)
    # support/resistance
    sup, res = support_resistance(df["low"].combine_first(df["close"]))
    df["support"] = sup
    df["resistance"] = res
    # volume as-is
    df["volume"] = df["volume"]
    return df
