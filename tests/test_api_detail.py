from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)


def test_analysis_detail_200_and_fields():
    r = client.get("/demo/analysis-detail?symbol=BTC-USD&periods=120&seed=abc&freq=1min")
    assert r.status_code == 200
    data = r.json()
    # required top-level fields
    for f in ["symbol", "mode", "engine_version", "signal", "confidence", "confidence_score", "reasons", "risk_score", "debug", "indicators"]:
        assert f in data


def test_same_seed_reproducible():
    p = "?symbol=BTC-USD&periods=120&seed=seed123&freq=1min"
    r1 = client.get(f"/demo/analysis-detail{p}")
    r2 = client.get(f"/demo/analysis-detail{p}")
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.text == r2.text


def test_max_10_indicator_rows():
    r = client.get("/demo/analysis-detail?symbol=BTC-USD&periods=50&seed=abc&freq=1min")
    assert r.status_code == 200
    data = r.json()
    indicators = data.get("indicators", [])
    assert isinstance(indicators, list)
    assert len(indicators) <= 10


def test_signal_value_valid():
    r = client.get("/demo/analysis-detail?symbol=BTC-USD&periods=120&seed=abc&freq=1min")
    assert r.status_code == 200
    data = r.json()
    assert data["signal"] in ["BUY", "SELL", "AVOID/WAIT"]


def test_json_serialization():
    r = client.get("/demo/analysis-detail?symbol=BTC-USD&periods=120&seed=abc&freq=1min")
    assert r.status_code == 200
    # ensure response is valid JSON
    json.loads(r.text)
