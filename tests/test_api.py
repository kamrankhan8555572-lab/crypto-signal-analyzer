from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["mode"] == "DEMO"


def test_demo_ohlcv():
    r = client.get("/demo/ohlcv?symbol=BTC-USD&periods=50&seed=abc")
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "BTC-USD"
    assert len(data["data"]) == 50


def test_demo_analyze():
    payload = {"symbol": "BTC-USD", "periods": 120, "seed": "abc", "freq": "1min"}
    r = client.post("/demo/analyze", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "DEMO"
    assert data["signal"] in ["BUY", "SELL", "AVOID/WAIT"]
