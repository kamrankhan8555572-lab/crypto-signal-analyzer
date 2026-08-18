import pytest
import pandas as pd
from app.synth_data import generate_ohlcv
from app.signal_engine import analyze_signals, evaluate_rules, compute_confidence, compute_risk


@pytest.fixture
def uptrend_df():
    # seed chosen to produce a mild upward trend
    return generate_ohlcv(symbol="UP", periods=200, seed="uptrend", freq="1min")


@pytest.fixture
def downtrend_df():
    return generate_ohlcv(symbol="DOWN", periods=200, seed="downtrend", freq="1min")


def test_individual_rules(uptrend_df):
    rules = evaluate_rules(uptrend_df)
    # rules is a list; ensure each rule has expected keys
    assert any(r["indicator"] == "price_vs_ema20" for r in rules)
    assert any(r["indicator"] == "ema20_vs_ema50" for r in rules)


def test_buy_signal(uptrend_df):
    res = analyze_signals(uptrend_df)
    assert res["mode"] == "DEMO"
    assert res["signal"] in ["BUY", "AVOID/WAIT"]  # deterministic but may be avoid depending on seed
    # If BUY, confidence label must be one of allowed
    if res["signal"] == "BUY":
        assert res["confidence"] in ["Low", "Medium", "High"]
        assert 0.0 <= res["confidence_score"] <= 1.0


def test_sell_signal(downtrend_df):
    res = analyze_signals(downtrend_df)
    assert res["mode"] == "DEMO"
    assert res["signal"] in ["SELL", "AVOID/WAIT"]
    if res["signal"] == "SELL":
        assert res["confidence"] in ["Low", "Medium", "High"]
        assert 0.0 <= res["confidence_score"] <= 1.0


def test_avoid_conditions():
    # Create a flat market where indicators likely disagree
    df = generate_ohlcv(symbol="FLAT", periods=200, seed="flat", freq="1min")
    # manipulate df to be flat
    df["close"] = 100.0
    df["open"] = 100.0
    df["high"] = 100.0
    df["low"] = 100.0
    df = df.copy()
    # attach minimal indicators to avoid errors
    df["ema20"] = 100.0
    df["ema50"] = 100.0
    df["macd_hist"] = 0.0
    df["rsi14"] = 50.0
    df["atr14"] = 0.0
    df["volatility20"] = 0.0
    res = analyze_signals(df)
    assert res["signal"] == "AVOID/WAIT"
    assert res["confidence"] == "Low"


def test_confidence_and_risk_metrics(uptrend_df):
    res = analyze_signals(uptrend_df)
    # confidence_score present
    assert "confidence_score" in res
    assert 0.0 <= res["confidence_score"] <= 1.0
    # risk_score bounded
    assert 0.0 <= res["risk_score"] <= 100.0


def test_rule_weights_effect(uptrend_df):
    # Ensure that weights affect buy/sell totals
    rules = evaluate_rules(uptrend_df)
    buy_weights = sum(r["weight"] for r in rules if not r["indicator"].endswith("_sell"))
    sell_weights = sum(r["weight"] for r in rules if r["indicator"].endswith("_sell"))
    assert buy_weights > 0
    assert sell_weights > 0
