#!/usr/bin/env python3
"""
Drift Sentinel — Synthetic Data Simulator

Simulates a deployed credit-risk ML model generating predictions over time.
Supports multiple drift injection modes so you can test the monitoring system.

Usage:
    # Basic: send 1000 predictions, no drift
    python scripts/simulate_drift.py --model-id <UUID> --n 1000

    # Covariate drift: age distribution shifts after 500 predictions
    python scripts/simulate_drift.py --model-id <UUID> --n 1000 --drift-type covariate --drift-at 500

    # Concept drift: model relationship changes
    python scripts/simulate_drift.py --model-id <UUID> --n 1000 --drift-type concept --drift-at 500

    # Prior probability shift: class balance changes
    python scripts/simulate_drift.py --model-id <UUID> --n 1000 --drift-type prior --drift-at 500

Requires the backend to be running on localhost:8000.
"""

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import numpy as np

BASE_URL = "http://localhost:8000/api/v1"
BATCH_SIZE = 200


def generate_features_normal(rng: np.random.Generator, n: int) -> list[dict[str, Any]]:
    """Baseline feature distribution (pre-drift)."""
    ages = rng.normal(loc=40, scale=12, size=n).clip(18, 80)
    incomes = rng.lognormal(mean=10.8, sigma=0.6, size=n).clip(15000, 300000)
    credit_scores = rng.normal(loc=680, scale=80, size=n).clip(300, 850)
    loan_amounts = rng.lognormal(mean=10.5, sigma=0.8, size=n).clip(1000, 500000)

    return [
        {
            "age": round(float(ages[i]), 1),
            "income": round(float(incomes[i]), 2),
            "credit_score": round(float(credit_scores[i]), 1),
            "loan_amount": round(float(loan_amounts[i]), 2),
        }
        for i in range(n)
    ]


def generate_features_drifted_covariate(
    rng: np.random.Generator, n: int, severity: float = 1.0
) -> list[dict[str, Any]]:
    """
    Covariate drift: age and income distributions shift.
    Simulates a new customer segment entering the system.
    severity: 0.0 = no drift, 1.0 = strong drift
    """
    # Age shifts younger (new fintech demographic)
    ages = rng.normal(loc=40 - 15 * severity, scale=8, size=n).clip(18, 80)
    # Income shifts lower
    incomes = rng.lognormal(mean=10.8 - 0.5 * severity, sigma=0.7, size=n).clip(15000, 300000)
    credit_scores = rng.normal(loc=680 - 40 * severity, scale=80, size=n).clip(300, 850)
    loan_amounts = rng.lognormal(mean=10.5, sigma=0.8, size=n).clip(1000, 500000)

    return [
        {
            "age": round(float(ages[i]), 1),
            "income": round(float(incomes[i]), 2),
            "credit_score": round(float(credit_scores[i]), 1),
            "loan_amount": round(float(loan_amounts[i]), 2),
        }
        for i in range(n)
    ]


def predict(features: list[dict], drift_type: str, is_post_drift: bool, rng: np.random.Generator):
    """
    Simulate model predictions. Concept drift changes the relationship
    between features and predictions.
    """
    results = []
    for f in features:
        # Baseline: credit score + income are strongest predictors
        score = (
            0.4 * (f["credit_score"] - 300) / 550
            + 0.3 * min(f["income"], 150000) / 150000
            + 0.2 * (f["age"] - 18) / 62
            - 0.1 * min(f["loan_amount"], 100000) / 100000
        )

        if is_post_drift and drift_type == "concept":
            # Concept drift: loan_amount becomes dominant predictor
            # (e.g. model was trained on personal loans, now seeing mortgages)
            score = (
                0.1 * (f["credit_score"] - 300) / 550
                + 0.1 * min(f["income"], 150000) / 150000
                + 0.1 * (f["age"] - 18) / 62
                - 0.7 * min(f["loan_amount"], 500000) / 500000
            )

        if is_post_drift and drift_type == "prior":
            # Prior probability shift: base rate of approval increases
            score += 0.3

        proba = float(1 / (1 + np.exp(-5 * (score - 0.4))))
        proba = float(np.clip(proba + rng.normal(0, 0.05), 0.01, 0.99))
        prediction = float(proba >= 0.5)
        results.append((prediction, proba))

    return results


def send_batch(
    model_id: str,
    features: list[dict],
    predictions: list[tuple],
    start_time: datetime,
    batch_index: int,
    client: httpx.Client,
) -> int:
    """POST a batch of predictions to the API."""
    payloads = []
    for i, (feat, (pred, proba)) in enumerate(zip(features, predictions)):
        ts = start_time + timedelta(seconds=batch_index * len(features) + i)
        payloads.append(
            {
                "ts": ts.isoformat(),
                "features": feat,
                "prediction": pred,
                "prediction_proba": proba,
            }
        )

    response = client.post(
        f"{BASE_URL}/models/{model_id}/predictions/batch",
        json={"predictions": payloads},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["ingested"]


def register_model(client: httpx.Client) -> str:
    """Register the demo credit-risk model if it doesn't exist."""
    # Check if model already exists
    models = client.get(f"{BASE_URL}/models").json()
    for m in models:
        if m["name"] == "credit-risk-demo":
            print(f"Using existing model: {m['id']}")
            return m["id"]

    response = client.post(
        f"{BASE_URL}/models",
        json={
            "name": "credit-risk-demo",
            "description": "Demo credit risk classifier for drift simulation",
            "task_type": "classification",
            "feature_schema": {
                "age": "float",
                "income": "float",
                "credit_score": "float",
                "loan_amount": "float",
            },
        },
    )
    response.raise_for_status()
    model_id = response.json()["id"]
    print(f"Registered new model: {model_id}")
    return model_id


def main():
    parser = argparse.ArgumentParser(description="Drift Sentinel synthetic data simulator")
    parser.add_argument("--model-id", default=None, help="Model UUID (auto-registers if omitted)")
    parser.add_argument("--n", type=int, default=500, help="Total number of predictions")
    parser.add_argument(
        "--drift-type",
        choices=["none", "covariate", "concept", "prior"],
        default="covariate",
        help="Type of drift to inject",
    )
    parser.add_argument(
        "--drift-at",
        type=int,
        default=None,
        help="Inject drift after this many predictions. Defaults to n//2.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--url", default=BASE_URL, help="API base URL")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    drift_at = args.drift_at if args.drift_at is not None else args.n // 2
    start_time = datetime.now(timezone.utc) - timedelta(minutes=90)

    print(f"\n{'='*60}")
    print(f"  Drift Sentinel — Data Simulator")
    print(f"  Total predictions : {args.n}")
    print(f"  Drift type        : {args.drift_type}")
    print(f"  Drift injected at : {drift_at}")
    print(f"  API               : {args.url}")
    print(f"{'='*60}\n")

    with httpx.Client(base_url="http://localhost:8000") as client:
        model_id = args.model_id or register_model(client)

        total_sent = 0
        batch_idx = 0

        while total_sent < args.n:
            batch_n = min(BATCH_SIZE, args.n - total_sent)
            is_post_drift = (args.drift_type != "none") and (total_sent >= drift_at)

            if is_post_drift:
                features = generate_features_drifted_covariate(rng, batch_n)
            else:
                features = generate_features_normal(rng, batch_n)

            preds = predict(features, args.drift_type, is_post_drift, rng)
            sent = send_batch(model_id, features, preds, start_time, batch_idx, client)

            total_sent += sent
            batch_idx += 1

            status = "DRIFT" if is_post_drift else "NORMAL"
            print(f"  [{status}] Batch {batch_idx:3d} — sent {sent:4d} | total: {total_sent:5d}/{args.n}")

            if is_post_drift and total_sent - drift_at == sent:
                print(f"\n  *** DRIFT INJECTED at prediction #{drift_at} ***\n")

            time.sleep(0.1)  # small delay to avoid overwhelming the API

    print(f"\n✓ Simulation complete. {total_sent} predictions sent to model {model_id}")
    print(f"  Check the drift dashboard or run: GET /api/v1/models/{model_id}/predictions")


if __name__ == "__main__":
    main()
