import pytest
from app.synth_data import generate_ohlcv
from app.signal_engine import analyze_signals
from app.indicators import attach_indicators
import pandas as pd


def test_uptrend_or_avoid():
    df = generate_ohlcv(symbol="UP", periods=200, seed="uptrend", freq="1min")
    res = analyze_signals(df)
    assert res["mode"] == "DEMO"
    assert res["signal"] in ["BUY", "AVOID/WAIT"]
    if res["signal"] == "BUY":
        assert res["confidence"] in ["Low", "Medium", "High"]
        assert 0.0 <= res["confidence_score"] <= 1.0


def test_downtrend_or_avoid():
    df = generate_ohlcv(symbol="DOWN", periods=200, seed="downtrend", freq="1min")
    res = analyze_signals(df)
    assert res["mode"] == "DEMO"
    assert res["signal"] in ["SELL", "AVOID/WAIT"]
    if res["signal"] == "SELL":
        assert res["confidence"] in ["Low", "Medium", "High"]
        assert 0.0 <= res["confidence_score"] <= 1.0


def test_flat_market_avoid():
    df = generate_ohlcv(symbol="FLAT", periods=200, seed="flat", freq="1min")
    df["close"] = 100.0
    df["open"] = 100.0
    df["high"] = 100.0
    df["low"] = 100.0
    df = df.copy()
    # attach minimal indicators to avoid errors
    df = attach_indicators(df)
    df["ema20"] = 100.0
    df["ema50"] = 100.0
    df["macd_hist"] = 0.0
    df["rsi14"] = 50.0
    df["atr14"] = 0.0
    df["volatility20"] = 0.0
    res = analyze_signals(df)
    assert res["signal"] == "AVOID/WAIT"
    assert res["confidence"] == "Low"


def test_high_volatility_blocks():
    # Create an uptrend but force high volatility in the latest row
    df = generate_ohlcv(symbol="UP", periods=200, seed="uptrend", freq="1min")
    df = attach_indicators(df)
    # Force last-row volatility and atr to high values
    df.at[df.index[-1], "volatility20"] = 0.6
    df.at[df.index[-1], "atr14"] = max(1.0, df.at[df.index[-1], "close"] * 0.05)
    res = analyze_signals(df)
    assert res["signal"] == "AVOID/WAIT"
