from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

AI_MODELS_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AI_MODELS_ROOT))

from service.main import app


DEFAULT_MODEL = AI_MODELS_ROOT / "models" / "graduate_admission_model.joblib"
SVR_MODEL = AI_MODELS_ROOT / "models" / "svr_regressor_personal.joblib"
VALID_FEATURES = {
    "GRE Score": 337,
    "TOEFL Score": 118,
    "University Rating": 4,
    "SOP": 4.5,
    "LOR": 4.5,
    "CGPA": 9.65,
    "Research": 1,
}


@pytest.fixture(autouse=True)
def configure_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PATH", str(DEFAULT_MODEL))
    monkeypatch.delenv("MODEL_METADATA_PATH", raising=False)


def test_health_reports_loaded_model_and_uptime() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["model_loaded"] is True
    assert response.json()["port"] == 8001
    assert response.json()["uptime_seconds"] >= 0


def test_model_info_reports_model_schema() -> None:
    with TestClient(app) as client:
        response = client.get("/model-info")

    assert response.status_code == 200
    assert response.json()["model_name"] == "Linear Regression"
    assert response.json()["features"] == list(VALID_FEATURES)
    assert response.json()["target"] == "Chance of Admit"


def test_predict_accepts_all_features_and_preserves_request_id() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            json={"features": VALID_FEATURES},
            headers={"X-Request-ID": "test-request-123"},
        )

    assert response.status_code == 200
    assert isinstance(response.json()["prediction"], float)
    assert response.json()["request_id"] == "test-request-123"
    assert response.headers["X-Request-ID"] == "test-request-123"


@pytest.mark.parametrize(
    ("features", "detail"),
    [
        ({**VALID_FEATURES, "GRE Score": 500}, "GRE Score must be between 290 and 340."),
        ({key: value for key, value in VALID_FEATURES.items() if key != "Research"}, "Missing features"),
        ({**VALID_FEATURES, "Unexpected": 1}, "Unexpected features"),
        ({**VALID_FEATURES, "CGPA": float("nan")}, "CGPA must be between"),
    ],
)
def test_predict_rejects_invalid_features(features: dict, detail: str) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/predict",
            content=json.dumps({"features": features}, allow_nan=True),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_input"
    assert detail in response.json()["detail"]
    assert response.json()["request_id"]


def test_predict_rejects_missing_features_object() -> None:
    with TestClient(app) as client:
        response = client.post("/predict", json={})

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_input"
    assert response.json()["request_id"]


def test_configured_artifact_metadata_is_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PATH", str(SVR_MODEL))
    with TestClient(app) as client:
        response = client.get("/model-info")

    assert response.status_code == 200
    assert response.json()["model_name"] == "SVR"
    assert response.json()["test_metrics"]["mae"] > 0