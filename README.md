# Drift Sentinel

Production ML monitoring platform that detects data drift, model degradation, and infrastructure anomalies in real time — with automated retraining triggers.

## Architecture

Five containerized services:

| Service | Role | Port |
|---------|------|------|
| `backend` | FastAPI REST + WebSocket API | 8000 |
| `db` | TimescaleDB (time-series metrics) | 5432 |
| `redis` | Celery broker + result backend | 6379 |
| `worker` | Celery background jobs | — |
| `mlflow` | Experiment tracking + model registry | 5001 |

## Quickstart

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/drift-sentinel
cd drift-sentinel
cp .env.example .env   # already configured for Docker
```

### 2. Start all services

```bash
cd infra
docker compose up --build
```

Wait ~60 seconds for first startup (TimescaleDB initialisation).

### 3. Verify health

```bash
curl http://localhost:8000/health
# {"status":"healthy","db":"ok","redis":"ok","version":"0.1.0"}
```

### 4. Open the API docs

Visit http://localhost:8000/docs — full interactive OpenAPI spec.

### 5. Run the drift simulator

```bash
# In a new terminal (Python 3.11+ with httpx and numpy)
pip install httpx numpy

# Simulate 1000 predictions with covariate drift after prediction 500
python scripts/simulate_drift.py --n 1000 --drift-type covariate --drift-at 500
```

## Development

### Run tests (no Docker required)

```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx aiosqlite coverage

# Unit tests only
pytest tests/unit/ -v

# Integration tests (uses in-memory SQLite)
pytest tests/integration/ -v

# Full suite with coverage
coverage run -m pytest && coverage report
```

### Useful Docker commands

```bash
# View logs
docker compose -f infra/docker-compose.yml logs backend -f

# Open a psql shell
docker exec -it drift_db psql -U drift -d drift_sentinel

# Check Celery worker
docker exec -it drift_worker celery -A app.workers.celery_app inspect active

# Restart just the backend after a code change
docker compose -f infra/docker-compose.yml restart backend
```

## API Reference

Full spec at `/docs` (Swagger) or `/redoc`.

### Key endpoints

```
POST   /api/v1/models                          Register a model
GET    /api/v1/models                          List models
POST   /api/v1/models/{id}/predictions         Ingest single prediction
POST   /api/v1/models/{id}/predictions/batch   Ingest batch (max 5000)
PATCH  /api/v1/models/{id}/ground-truth        Reconcile labels
GET    /api/v1/models/{id}/predictions         Retrieve logs (paginated)
GET    /health                                  Health check
```

### Quick example

```bash
# Register a model
curl -X POST http://localhost:8000/api/v1/models \
  -H "Content-Type: application/json" \
  -d '{
    "name": "credit-risk-v1",
    "task_type": "classification",
    "feature_schema": {"age": "float", "income": "float", "credit_score": "float"}
  }'

# Ingest a prediction (use the model ID from above)
curl -X POST http://localhost:8000/api/v1/models/MODEL_ID/predictions \
  -H "Content-Type: application/json" \
  -d '{
    "features": {"age": 35.0, "income": 60000.0, "credit_score": 720.0},
    "prediction": 1.0,
    "prediction_proba": 0.84
  }'
```

## Project Roadmap

- [x] **Week 1–2**: Data foundation — ingestion API, TimescaleDB, Docker, tests, simulator
- [ ] **Week 3–4**: Drift detection engine (KS, PSI, JSD, MMD)
- [ ] **Week 5–6**: ML pipeline, MLflow integration, SHAP explainability, retrain trigger
- [ ] **Week 7–8**: Auth (JWT), rate limiting, load testing (Locust)
- [ ] **Week 9–10**: React dashboard with live charts (WebSocket)
- [ ] **Week 11–12**: AWS ECS deployment, GitHub Actions CI/CD, DS analysis notebook

## Tech Stack

Python 3.11 · FastAPI · SQLAlchemy (async) · TimescaleDB · Redis · Celery · MLflow · scikit-learn · XGBoost · SHAP · React · Docker · AWS ECS
