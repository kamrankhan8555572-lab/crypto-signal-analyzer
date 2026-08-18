from typing import List, Optional
import pandas as pd


def analyze_signals(df: pd.DataFrame) -> dict:
    """Deterministic explainable signal engine based on indicator rules.

    Rules (DEMO, deterministic):
      - BUY when:
         - close > ema20
         - ema20 > ema50
         - macd_hist > 0
         - rsi14 between 30 and 70 (not overbought)
      - SELL when:
         - close < ema20
         - ema20 < ema50
         - macd_hist < 0
         - rsi14 > 30 (confirmation)
      - Otherwise: AVOID/WAIT

    Confidence: computed from number of rules satisfied and volatility/atr adjustments.
    Risk score: normalized from ATR and volatility.
    Invalidation price: if opposite EMA cross occurs, set invalidation to ema50.
    """
    out = {}
    latest = df.iloc[-1]
    symbol = "DEMO"

    reasons = []
    # Evaluate rules
    close = float(latest["close"])
    ema20 = float(latest["ema20"])
    ema50 = float(latest["ema50"])
    macd_hist = float(latest["macd_hist"])
    rsi = float(latest["rsi14"])
    atr = float(latest["atr14"])
    vol20 = float(latest["volatility20"] if not pd.isna(latest["volatility20"]) else 0.0)

    # Rule checks
    r_close_above_ema20 = close > ema20
    r_ema20_above_ema50 = ema20 > ema50
    r_macd_pos = macd_hist > 0
    r_rsi_ok = (rsi > 20) and (rsi < 70)

    reasons.append({"indicator": "price_vs_ema20", "description": f"close ({close:.4f}) > ema20 ({ema20:.4f})", "passed": r_close_above_ema20})
    reasons.append({"indicator": "ema20_vs_ema50", "description": f"ema20 ({ema20:.4f}) > ema50 ({ema50:.4f})", "passed": r_ema20_above_ema50})
    reasons.append({"indicator": "macd_hist", "description": f"macd_hist ({macd_hist:.6f}) > 0", "passed": r_macd_pos})
    reasons.append({"indicator": "rsi14", "description": f"rsi14 ({rsi:.2f}) between optimal bounds", "passed": r_rsi_ok})

    buy_score = sum([r_close_above_ema20, r_ema20_above_ema50, r_macd_pos, r_rsi_ok])

    # SELL checks (mirror-ish)
    s_close_below_ema20 = close < ema20
    s_ema20_below_ema50 = ema20 < ema50
    s_macd_neg = macd_hist < 0
    s_rsi_confirm = rsi > 30

    reasons.append({"indicator": "price_vs_ema20_sell", "description": f"close ({close:.4f}) < ema20 ({ema20:.4f})", "passed": s_close_below_ema20})
    reasons.append({"indicator": "ema20_vs_ema50_sell", "description": f"ema20 ({ema20:.4f}) < ema50 ({ema50:.4f})", "passed": s_ema20_below_ema50})
    reasons.append({"indicator": "macd_hist_sell", "description": f"macd_hist ({macd_hist:.6f}) < 0", "passed": s_macd_neg})
    reasons.append({"indicator": "rsi14_sell", "description": f"rsi14 ({rsi:.2f}) confirmation", "passed": s_rsi_confirm})

    sell_score = sum([s_close_below_ema20, s_ema20_below_ema50, s_macd_neg, s_rsi_confirm])

    # Decide signal
    if buy_score >= 3 and sell_score == 0:
        signal = "BUY"
    elif sell_score >= 3 and buy_score == 0:
        signal = "SELL"
    else:
        signal = "AVOID/WAIT"

    # Confidence
    raw_conf = 0
    if signal == "BUY":
        raw_conf = buy_score
    elif signal == "SELL":
        raw_conf = sell_score
    else:
        raw_conf = 0

    # Adjust by volatility and ATR: more volatility lowers confidence
    vol_adj = max(0.0, 1.0 - min(1.0, vol20 * 10))
    atr_adj = max(0.0, 1.0 - min(1.0, atr / max(1e-8, close) * 50))
    conf_score = raw_conf * vol_adj * atr_adj

    if conf_score >= 3:
        confidence = "High"
    elif conf_score >= 1.5:
        confidence = "Medium"
    else:
        confidence = "Low"

    # Risk score: derived from ATR relative to price and volatility
    risk = min(100.0, (atr / max(1e-8, close)) * 100.0 * (1 + vol20 * 10))

    # Invalidation level: crossing ema50 or major support
    invalidation_price = float(latest["ema50"]) if signal in ["BUY", "SELL"] else None

    out = {
        "symbol": symbol,
        "mode": "DEMO",
        "signal": signal,
        "confidence": confidence,
        "reasons": reasons,
        "risk_score": round(float(risk), 3),
        "invalidation_price": invalidation_price,
        "latest": {
            "timestamp": str(latest.name),
            "open": float(latest["open"]),
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "close": float(latest["close"]),
            "volume": int(latest["volume"]),
        },
        "debug": {
            "buy_score": int(buy_score),
            "sell_score": int(sell_score),
            "vol_adj": vol_adj,
            "atr_adj": atr_adj,
            "raw_conf": raw_conf,
        },
    }
    return out
