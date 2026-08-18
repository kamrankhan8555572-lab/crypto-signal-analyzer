"""Demo-mode FastAPI backend for Crypto Signal Analyzer

DEMO MODE - Educational and Research Use Only
No live trading, no accounts, no orders.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.synth_data import generate_ohlcv
from app.indicators import attach_indicators
from app.signal_engine import analyze_signals
from app.schemas import AnalyzeRequest, AnalyzeResponse

app = FastAPI(title="Crypto Signal Analyzer (DEMO MODE)", description="DEMO MODE - Educational and Research Use Only")


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "DEMO", "message": "Demo backend running - Educational/Research Only"}


@app.get("/demo/ohlcv")
async def demo_ohlcv(symbol: str = "BTC-USD", periods: int = 200, seed: str = "demo", freq: str = "1min"):
    try:
        df = generate_ohlcv(symbol=symbol, periods=periods, seed=seed, freq=freq)
        # return limited view
        records = df.reset_index().to_dict(orient="records")
        return JSONResponse(content={
            "symbol": symbol,
            "periods": periods,
            "freq": freq,
            "demo_mode": True,
            "data": jsonable_encoder(records)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/demo/analysis-detail")
async def demo_analysis_detail(symbol: str = "BTC-USD", periods: int = 200, seed: str = "demo", freq: str = "1min"):
    """DEMO-only analysis detail endpoint.

    Returns structured analysis including rule results and a small sample of recent indicator rows (max 10).
    All values are JSON-serializable (uses jsonable_encoder where needed).
    """
    try:
        # deterministic data
        df = generate_ohlcv(symbol=symbol, periods=periods, seed=seed, freq=freq)
        df = attach_indicators(df)
        analysis = analyze_signals(df)

        # prepare limited recent indicator rows (max 10)
        max_rows = 10
        recent = df.tail(max_rows).reset_index()
        recent_records = recent.to_dict(orient="records")

        payload = {
            "symbol": symbol,
            "mode": "DEMO",
            "engine_version": analysis.get("engine_version"),
            "signal": analysis.get("signal"),
            "confidence": analysis.get("confidence"),
            "confidence_score": analysis.get("confidence_score"),
            "reasons": analysis.get("reasons"),
            "risk_score": analysis.get("risk_score"),
            "invalidation_price": analysis.get("invalidation_price"),
            "debug": analysis.get("debug"),
            "indicators": jsonable_encoder(recent_records),
        }
        return JSONResponse(content=jsonable_encoder(payload))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/demo/analyze", response_model=AnalyzeResponse)
async def demo_analyze(req: AnalyzeRequest):
    # Generate deterministic data
    df = generate_ohlcv(symbol=req.symbol, periods=req.periods, seed=req.seed, freq=req.freq)
    df = attach_indicators(df)
    analysis = analyze_signals(df)
    return analysis
