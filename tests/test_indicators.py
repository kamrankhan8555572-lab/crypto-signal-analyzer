import pandas as pd
from app.synth_data import generate_ohlcv
from app.indicators import attach_indicators


def test_indicators_shape():
    df = generate_ohlcv(symbol="TEST", periods=100, seed="s", freq="1min")
    df2 = attach_indicators(df)
    # ensure indicator columns exist
    for col in ["ema20", "ema50", "ema200", "rsi14", "macd", "macd_signal", "macd_hist", "bb_upper", "bb_mid", "bb_lower", "atr14", "volatility20", "support", "resistance"]:
        assert col in df2.columns
    assert len(df2) == 100
