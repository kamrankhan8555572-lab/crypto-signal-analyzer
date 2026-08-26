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


def safe_indicator(row, col: str) -> tuple:
    """Extract indicator value safely. Returns (value, is_valid)."""
    try:
        val = row.get(col)
        if pd.isna(val):
            return 0.0, False
        return float(val), True
    except:
        return 0.0, False


def evaluate_rules(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Evaluate rule results using indicator columns.

    If the provided DataFrame does not already contain the expected indicator
    columns (e.g., 'ema20'), this function will attach indicators using the
    standard attach_indicators helper. This keeps the function resilient when
    callers pass raw OHLCV data.
    
    Safe NaN handling: if an indicator is NaN/missing, mark that rule as failed
    with explicit explanation rather than using artificial default values.
    """
    # If indicators are missing (tests may pass raw OHLCV), compute them.
    if "ema20" not in df.columns:
        # use a copy to avoid mutating caller's DataFrame
        df = attach_indicators(df.copy())

    latest = df.iloc[-1]
    
    # Extract values with NaN checks — fail rules individually, not globally
    try:
        close = float(latest["close"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Critical data missing: close price")

    # For indicators: if NaN, mark rule as failed with explanation
    ema20, ema20_valid = safe_indicator(latest, "ema20")
    ema50, ema50_valid = safe_indicator(latest, "ema50")
    macd_hist, macd_valid = safe_indicator(latest, "macd_hist")
    rsi, rsi_valid = safe_indicator(latest, "rsi14")

    rules = []

    # BUY rules — if indicator NaN/missing, mark as failed
    if not ema20_valid:
        rules.append(_make_rule(
            id="r1",
            indicator="price_vs_ema20",
            passed=False,
            value=None,
            threshold={"operator":">", "rhs": "EMA20"},
            weight=RULE_WEIGHTS["price_vs_ema20"],
            explanation="Cannot evaluate: EMA20 is NaN/missing",
        ))
    else:
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

    if not ema50_valid or not ema20_valid:
        rules.append(_make_rule(
            id="r2",
            indicator="ema20_vs_ema50",
            passed=False,
            value=None,
            threshold={"operator":">", "rhs": "EMA50"},
            weight=RULE_WEIGHTS["ema20_vs_ema50"],
            explanation="Cannot evaluate: EMA20 or EMA50 is NaN/missing",
        ))
    else:
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

    if not macd_valid:
        rules.append(_make_rule(
            id="r3",
            indicator="macd_hist_pos",
            passed=False,
            value=None,
            threshold={"operator":">", "rhs": 0.0},
            weight=RULE_WEIGHTS["macd_hist_pos"],
            explanation="Cannot evaluate: MACD histogram is NaN/missing",
        ))
    else:
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

    if not rsi_valid:
        rules.append(_make_rule(
            id="r4",
            indicator="rsi_optimal",
            passed=False,
            value=None,
            threshold={"low": 20, "high": 70},
            weight=RULE_WEIGHTS["rsi_optimal"],
            explanation="Cannot evaluate: RSI is NaN/missing",
        ))
    else:
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

    # SELL rules (mirror) — same logic
    if not ema20_valid:
        rules.append(_make_rule(
            id="s1",
            indicator="price_vs_ema20_sell",
            passed=False,
            value=None,
            threshold={"operator":"<", "rhs": "EMA20"},
            weight=RULE_WEIGHTS["price_vs_ema20_sell"],
            explanation="Cannot evaluate: EMA20 is NaN/missing",
        ))
    else:
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

    if not ema50_valid or not ema20_valid:
        rules.append(_make_rule(
            id="s2",
            indicator="ema20_vs_ema50_sell",
            passed=False,
            value=None,
            threshold={"operator":"<", "rhs": "EMA50"},
            weight=RULE_WEIGHTS["ema20_vs_ema50_sell"],
            explanation="Cannot evaluate: EMA20 or EMA50 is NaN/missing",
        ))
    else:
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

    if not macd_valid:
        rules.append(_make_rule(
            id="s3",
            indicator="macd_hist_neg",
            passed=False,
            value=None,
            threshold={"operator":"<", "rhs": 0.0},
            weight=RULE_WEIGHTS["macd_hist_neg"],
            explanation="Cannot evaluate: MACD histogram is NaN/missing",
        ))
    else:
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

    if not rsi_valid:
        rules.append(_make_rule(
            id="s4",
            indicator="rsi_confirm_sell",
            passed=False,
            value=None,
            threshold={"operator":">", "rhs": 30},
            weight=RULE_WEIGHTS["rsi_confirm_sell"],
            explanation="Cannot evaluate: RSI is NaN/missing",
        ))
    else:
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


def compute_confidence(score: float, max_score: float, vol20: float, atr: float, close: float, 
                      vol20_valid: bool = True, atr_valid: bool = True) -> (str, float):
    """Compute a bounded, transparent confidence score and label.

    - score: weighted sum for the chosen direction
    - max_score: maximum possible weighted sum
    - vol20 and atr reduce confidence
    - vol20_valid, atr_valid: flags if metrics are actually available
    - If metrics missing, reduce confidence floor to avoid false positives
    Returns (label, conf_value between 0 and 1)
    """
    if max_score <= 0:
        return "Low", 0.0

    base = score / max_score
    # Volatility and ATR adjustments: map to [0,1]
    vol_factor = max(0.0, 1.0 - min(1.0, vol20 * 10))
    atr_factor = max(0.0, 1.0 - min(1.0, (atr / max(1e-8, close)) * 50))
    conf = base * vol_factor * atr_factor
    
    # If metrics missing, apply conservative penalty to avoid false positives
    if not vol20_valid or not atr_valid:
        conf = conf * 0.7  # Reduce by 30% if metrics degraded
    
    conf = max(0.0, min(1.0, conf))

    if conf >= 0.75:
        label = "High"
    elif conf >= 0.4:
        label = "Medium"
    else:
        label = "Low"
    return label, conf


def compute_risk(atr: float, close: float, vol20: float, 
                atr_valid: bool = True, vol20_valid: bool = True) -> float:
    """Compute a bounded risk score 0-100.
    
    If ATR or volatility missing, raise risk conservatively.
    """
    if close <= 0:
        return 100.0
    raw = (atr / close) * 100.0 * (1.0 + vol20 * 10.0)
    risk = float(max(0.0, min(100.0, raw)))
    
    # If metrics missing, add conservative penalty to risk
    if not atr_valid or not vol20_valid:
        risk = risk + 25.0  # Add 25 points to risk if metrics degraded
    
    risk = float(max(0.0, min(100.0, risk)))  # Ensure still bounded
    return risk


def analyze_signals(df: pd.DataFrame) -> Dict[str, Any]:
    """Produce structured rule results and decide BUY/SELL/AVOID deterministically.

    Validates minimum data, safely handles NaN indicators (fail rules individually),
    and conservatively reduces confidence if critical metrics are missing.
    
    Raises ValueError if insufficient data (< 20 rows) or critical OHLC missing.
    Returns a dict with signal (BUY/SELL/AVOID/WAIT), confidence, and detailed reasons.
    """
    # ===== Step 1: Validate minimum rows and critical OHLC data =====
    if df is None or len(df) == 0:
        raise ValueError("DataFrame is empty or None")
    
    if len(df) < 20:
        raise ValueError(f"Insufficient data: need at least 20 rows, got {len(df)}")
    
    # Ensure indicators are present for downstream logic
    if "ema20" not in df.columns:
        df = attach_indicators(df.copy())

    latest = df.iloc[-1]
    
    # Validate critical OHLC data exists and is not NaN
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns or pd.isna(latest[col]):
            raise ValueError(f"Critical OHLC data missing or NaN: {col}")
    
    symbol = "DEMO"
    
    # ===== Step 2: Evaluate rules with safe NaN handling =====
    rules = evaluate_rules(df)

    # ===== Step 3: Compute signal from rules =====
    buy_rules = [r for r in rules if not r["indicator"].endswith("_sell")]
    sell_rules = [r for r in rules if r["indicator"].endswith("_sell")]

    buy_score = sum([r["weight"] for r in buy_rules if r["passed"]])
    sell_score = sum([r["weight"] for r in sell_rules if r["passed"]])
    max_buy = sum([r["weight"] for r in buy_rules])
    max_sell = sum([r["weight"] for r in sell_rules])

    # Decide signal deterministically: require majority of weighted rules and no strong opposite
    signal = "AVOID/WAIT"
    if buy_score >= max(1, int(max_buy * 0.6)) and sell_score == 0:
        signal = "BUY"
    elif sell_score >= max(1, int(max_sell * 0.6)) and buy_score == 0:
        signal = "SELL"
    else:
        signal = "AVOID/WAIT"

    # ===== Step 4: Extract metrics with quality checks =====
    # Check if volatility and ATR are actually available and valid (not NaN)
    vol20_raw = latest.get("volatility20")
    atr_raw = latest.get("atr14")
    
    vol20_valid = vol20_raw is not None and not pd.isna(vol20_raw)
    atr_valid = atr_raw is not None and not pd.isna(atr_raw)
    
    vol20 = float(vol20_raw) if vol20_valid else 0.0
    atr = float(atr_raw) if atr_valid else 0.0
    close = float(latest["close"])
    
    # Flag: if critical metrics missing, reduce confidence and raise risk
    metrics_quality = "full" if (vol20_valid and atr_valid) else "degraded"

    # ===== Step 5: Compute confidence and risk =====
    if signal == "BUY":
        conf_label, conf_value = compute_confidence(buy_score, max_buy, vol20, atr, close, vol20_valid, atr_valid)
    elif signal == "SELL":
        conf_label, conf_value = compute_confidence(sell_score, max_sell, vol20, atr, close, vol20_valid, atr_valid)
    else:
        conf_label, conf_value = "Low", 0.0

    risk = compute_risk(atr, close, vol20, atr_valid, vol20_valid)

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
            "metrics_quality": metrics_quality,
        },
    }
    return out
