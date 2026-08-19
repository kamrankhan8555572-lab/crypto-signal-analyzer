from typing import List, Optional, Dict, Any
import pandas as pd
from app.indicators import attach_indicators

# Engine version
ENGINE_VERSION = "engine_v0.1-demo"

# Define rule weights (integer weights)
# We use symmetric rules for BUY and SELL with clear weights for explainability.
RULE_WEIGHTS = {
    "price_vs_ema20": 2,
    "ema20_vs_ema50": 2,
    "macd_hist_pos": 1,
    "rsi_optimal": 1,
    # sell counterparts use same weights
    "price_vs_ema20_sell": 2,
    "ema20_vs_ema50_sell": 2,
    "macd_hist_neg": 1,
    "rsi_confirm_sell": 1,
}


def _make_rule(id: str, indicator: str, passed: bool, value: Optional[float], threshold: Optional[Any], weight: int, explanation: str) -> Dict[str, Any]:
    return {
        "id": id,
        "indicator": indicator,
        "passed": passed,
        "value": float(value) if value is not None else None,
        "threshold": threshold,
        "weight": int(weight),
        "explanation": explanation,
    }


def evaluate_rules(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Evaluate rule results using indicator columns.

    If the provided DataFrame does not already contain the expected indicator
    columns (e.g., 'ema20'), this function will attach indicators using the
    standard attach_indicators helper. This keeps the function resilient when
    callers pass raw OHLCV data.
    """
    # If indicators are missing (tests may pass raw OHLCV), compute them.
    if "ema20" not in df.columns:
        # use a copy to avoid mutating caller's DataFrame
        df = attach_indicators(df.copy())

    latest = df.iloc[-1]
    close = float(latest["close"])
    ema20 = float(latest["ema20"])
    ema50 = float(latest["ema50"])
    macd_hist = float(latest.get("macd_hist", 0.0))
    rsi = float(latest.get("rsi14", 0.0))

    rules = []

    # BUY rules
    r1 = close > ema20
    rules.append(_make_rule(
        id="r1",
        indicator="price_vs_ema20",
        passed=r1,
        value=close - ema20,
        threshold={"operator":">", "rhs": ema20},
        weight=RULE_WEIGHTS["price_vs_ema20"],
        explanation=f"Close ({close:.4f}) {'>' if r1 else '<='} EMA20 ({ema20:.4f})",
    ))

    r2 = ema20 > ema50
    rules.append(_make_rule(
        id="r2",
        indicator="ema20_vs_ema50",
        passed=r2,
        value=ema20 - ema50,
        threshold={"operator":">", "rhs": ema50},
        weight=RULE_WEIGHTS["ema20_vs_ema50"],
        explanation=f"EMA20 ({ema20:.4f}) {'>' if r2 else '<='} EMA50 ({ema50:.4f})",
    ))

    r3 = macd_hist > 0
    rules.append(_make_rule(
        id="r3",
        indicator="macd_hist_pos",
        passed=r3,
        value=macd_hist,
        threshold={"operator":">", "rhs": 0.0},
        weight=RULE_WEIGHTS["macd_hist_pos"],
        explanation=f"MACD hist ({macd_hist:.6f}) {'>' if r3 else '<='} 0",
    ))

    r4 = (rsi > 20) and (rsi < 70)
    rules.append(_make_rule(
        id="r4",
        indicator="rsi_optimal",
        passed=r4,
        value=rsi,
        threshold={"low": 20, "high": 70},
        weight=RULE_WEIGHTS["rsi_optimal"],
        explanation=f"RSI ({rsi:.2f}) in (20,70) => {'ok' if r4 else 'not ok'}",
    ))

    # SELL rules (mirror)
    s1 = close < ema20
    rules.append(_make_rule(
        id="s1",
        indicator="price_vs_ema20_sell",
        passed=s1,
        value=ema20 - close,
        threshold={"operator":"<", "rhs": ema20},
        weight=RULE_WEIGHTS["price_vs_ema20_sell"],
        explanation=f"Close ({close:.4f}) {'<' if s1 else '>='} EMA20 ({ema20:.4f})",
    ))

    s2 = ema20 < ema50
    rules.append(_make_rule(
        id="s2",
        indicator="ema20_vs_ema50_sell",
        passed=s2,
        value=ema50 - ema20,
        threshold={"operator":"<", "rhs": ema50},
        weight=RULE_WEIGHTS["ema20_vs_ema50_sell"],
        explanation=f"EMA20 ({ema20:.4f}) {'<' if s2 else '>='} EMA50 ({ema50:.4f})",
    ))

    s3 = macd_hist < 0
    rules.append(_make_rule(
        id="s3",
        indicator="macd_hist_neg",
        passed=s3,
        value=macd_hist,
        threshold={"operator":"<", "rhs": 0.0},
        weight=RULE_WEIGHTS["macd_hist_neg"],
        explanation=f"MACD hist ({macd_hist:.6f}) {'<' if s3 else '>='} 0",
    ))

    s4 = rsi > 30
    rules.append(_make_rule(
        id="s4",
        indicator="rsi_confirm_sell",
        passed=s4,
        value=rsi,
        threshold={"operator":">", "rhs": 30},
        weight=RULE_WEIGHTS["rsi_confirm_sell"],
        explanation=f"RSI ({rsi:.2f}) {'>' if s4 else '<='} 30",
    ))

    return rules


def compute_confidence(score: float, max_score: float, vol20: float, atr: float, close: float) -> (str, float):
    """Compute a bounded, transparent confidence score and label.

    - score: weighted sum for the chosen direction
    - max_score: maximum possible weighted sum
    - vol20 and atr reduce confidence
    Returns (label, conf_value between 0 and 1)
    """
    if max_score <= 0:
        return "Low", 0.0

    base = score / max_score
    # Volatility and ATR adjustments: map to [0,1]
    vol_factor = max(0.0, 1.0 - min(1.0, vol20 * 10))
    atr_factor = max(0.0, 1.0 - min(1.0, (atr / max(1e-8, close)) * 50))
    conf = base * vol_factor * atr_factor
    conf = max(0.0, min(1.0, conf))

    if conf >= 0.75:
        label = "High"
    elif conf >= 0.4:
        label = "Medium"
    else:
        label = "Low"
    return label, conf


def compute_risk(atr: float, close: float, vol20: float) -> float:
    """Compute a bounded risk score 0-100."""
    if close <= 0:
        return 100.0
    raw = (atr / close) * 100.0 * (1.0 + vol20 * 10.0)
    return float(max(0.0, min(100.0, raw)))


def analyze_signals(df: pd.DataFrame) -> Dict[str, Any]:
    """Produce structured rule results and decide BUY/SELL/AVOID deterministically.

    Returns a dict compatible with previous API but reasons now contain detailed RuleResult entries.
    """
    # Ensure indicators are present for downstream logic
    if "ema20" not in df.columns:
        df = attach_indicators(df.copy())

    latest = df.iloc[-1]
    symbol = "DEMO"

    rules = evaluate_rules(df)

    # Sum weights for buy and sell
    buy_rules = [r for r in rules if not r["indicator"].endswith("_sell")]
    sell_rules = [r for r in rules if r["indicator"].endswith("_sell")]

    buy_score = sum([r["weight"] for r in buy_rules if r["passed"]])
    sell_score = sum([r["weight"] for r in sell_rules if r["passed"]])
    max_buy = sum([r["weight"] for r in buy_rules])
    max_sell = sum([r["weight"] for r in sell_rules])

    # Decision fractions
    buy_fraction = (buy_score / max_buy) if max_buy > 0 else 0.0
    sell_fraction = (sell_score / max_sell) if max_sell > 0 else 0.0

    # metrics for confidence/risk
    vol20 = float(latest.get("volatility20", 0.0) if not pd.isna(latest.get("volatility20", 0.0)) else 0.0)
    atr = float(latest.get("atr14", 0.0) if not pd.isna(latest.get("atr14", 0.0)) else 0.0)
    close = float(latest["close"])

    # Decision thresholds (as requested)
    strong_majority_frac = 0.6
    weak_majority_frac = 0.4
    opposite_tolerance_frac = 0.2
    volatility_block_frac = 0.5
    atr_block_ratio = 0.03

    # Safety overrides: high volatility or ATR blocks active signals
    atr_ratio = (atr / close) if close > 0 else float('inf')
    decision_reason = "default"
    signal = "AVOID/WAIT"

    if vol20 >= volatility_block_frac:
        signal = "AVOID/WAIT"
        decision_reason = "high_volatility"
    elif atr_ratio >= atr_block_ratio:
        signal = "AVOID/WAIT"
        decision_reason = "high_atr"
    else:
        # Strong buy
        if (buy_fraction >= strong_majority_frac) and (sell_fraction <= opposite_tolerance_frac):
            signal = "BUY"
            decision_reason = "strong_buy"
        # Strong sell
        elif (sell_fraction >= strong_majority_frac) and (buy_fraction <= opposite_tolerance_frac):
            signal = "SELL"
            decision_reason = "strong_sell"
        # Weak/leaning signals: conservative -> AVOID/WAIT
        elif (buy_fraction >= weak_majority_frac) and (buy_fraction > sell_fraction):
            signal = "AVOID/WAIT"
            decision_reason = "lean_buy_avoid"
        elif (sell_fraction >= weak_majority_frac) and (sell_fraction > buy_fraction):
            signal = "AVOID/WAIT"
            decision_reason = "lean_sell_avoid"
        else:
            signal = "AVOID/WAIT"
            decision_reason = "default"

    if signal == "BUY":
        conf_label, conf_value = compute_confidence(buy_score, max_buy, vol20, atr, close)
    elif signal == "SELL":
        conf_label, conf_value = compute_confidence(sell_score, max_sell, vol20, atr, close)
    else:
        conf_label, conf_value = "Low", 0.0

    risk = compute_risk(atr, close, vol20)

    invalidation_price = float(latest["ema50"]) if signal in ["BUY", "SELL"] else None

    out = {
        "symbol": symbol,
        "mode": "DEMO",
        "engine_version": ENGINE_VERSION,
        "signal": signal,
        "confidence": conf_label,
        "confidence_score": round(float(conf_value), 4),
        "reasons": rules,
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
            "max_buy": int(max_buy),
            "max_sell": int(max_sell),
            "volatility20": vol20,
            "atr14": atr,
            "decision_reason": decision_reason,
        },
    }
    return out
