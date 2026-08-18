# Basic README for demo backend

This repository addition adds a DEMO MODE FastAPI backend for the Crypto Signal Analyzer.

Important:
- DEMO MODE - Educational and Research Use Only
- No live trading, no orders, no accounts

How to run locally:
- python -m venv venv
- source venv/bin/activate (or venv\Scripts\activate on Windows)
- pip install -r requirements.txt
- uvicorn app.main:app --reload --port 8000

Endpoints:
- GET /health
- GET /demo/ohlcv?symbol=...&periods=...&seed=...
- POST /demo/analyze  (body: symbol, periods, seed, freq)
