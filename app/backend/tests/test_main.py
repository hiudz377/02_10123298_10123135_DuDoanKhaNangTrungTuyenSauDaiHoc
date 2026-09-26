from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app


VALID_FEATURES = {
    "GRE Score": 337,
    "TOEFL Score": 118,
    "University Rating": 4,
    "SOP": 4.5,
    "LOR": 4.5,
    "CGPA": 9.65,
    "Research": 1,
}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def set_ai_response(client: TestClient, handler) -> None:
    old_client = client.portal.call(lambda: app.state.ai_client)
    client.portal.call(lambda: old_client.aclose())
    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client.portal.call(lambda: setattr(app.state, "ai_client", mock_client))


def test_health_checks_ai_service_and_reports_uptime(client: TestClient) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok", "port": 8001})

    set_ai_response(client, handler)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["ai_service"]["port"] == 8001
    assert response.json()["uptime_seconds"] >= 0


def test_predict_forwards_exact_ai_contract_and_returns_chance(client: TestClient) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/predict"
        assert request.headers["X-Request-ID"] == "frontend-request-1"
        body = json.loads(request.content)
        assert body["features"] == VALID_FEATURES
        assert body["request_id"] == "frontend-request-1"
        return httpx.Response(
            200,
            json={
                "prediction": 0.87,
                "model_name": "Linear Regression",
                "model_version": "1.0.0",
                "request_id": "frontend-request-1",
            },
        )

    set_ai_response(client, handler)
    response = client.post(
        "/predict",
        json={"features": VALID_FEATURES},
        headers={"X-Request-ID": "frontend-request-1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "prediction": 0.87,
        "chance_of_admit": 0.87,
        "model_name": "Linear Regression",
        "model_version": "1.0.0",
        "request_id": "frontend-request-1",
    }
    assert response.headers["X-Request-ID"] == "frontend-request-1"


def test_frontend_api_route_alias(client: TestClient) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"prediction": 0.8, "request_id": "alias-request"})

    set_ai_response(client, handler)
    response = client.post(
        "/api/predict",
        json={"features": VALID_FEATURES, "request_id": "alias-request"},
    )

    assert response.status_code == 200
    assert response.json()["chance_of_admit"] == 0.8


def test_predict_accepts_integer_sop_and_lor_values(client: TestClient) -> None:
    features = {**VALID_FEATURES, "SOP": 4, "LOR": 4}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["features"]["SOP"] == 4.0
        assert body["features"]["LOR"] == 4.0
        return httpx.Response(200, json={"prediction": 0.8, "request_id": body["request_id"]})

    set_ai_response(client, handler)
    response = client.post("/predict", json={"features": features})

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("features", "detail"),
    [
        ({**VALID_FEATURES, "GRE Score": 350}, "less than or equal to 340"),
        ({key: value for key, value in VALID_FEATURES.items() if key != "Research"}, "Field required"),
        ({**VALID_FEATURES, "Other": 1}, "Extra inputs are not permitted"),
        ({**VALID_FEATURES, "SOP": 4.2}, "half-point increments"),
    ],
)
def test_predict_rejects_invalid_input_without_calling_ai(
    client: TestClient, features: dict, detail: str
) -> None:
    def unexpected_call(request: httpx.Request) -> httpx.Response:
        pytest.fail("Invalid input must not be sent to the AI Service")

    set_ai_response(client, unexpected_call)
    response = client.post("/predict", json={"features": features})

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_input"
    assert detail in response.json()["detail"]
    assert response.json()["request_id"]


def test_predict_maps_ai_connection_error_to_503(client: TestClient) -> None:
    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("service unavailable", request=request)

    set_ai_response(client, unavailable)
    response = client.post("/predict", json={"features": VALID_FEATURES})

    assert response.status_code == 503
    assert response.json()["error"] == "ai_service_unavailable"
    assert response.json()["request_id"]


def test_predict_maps_ai_timeout_to_504(client: TestClient) -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    set_ai_response(client, timeout)
    response = client.post("/predict", json={"features": VALID_FEATURES})

    assert response.status_code == 504
    assert response.json()["error"] == "ai_service_timeout"


def test_predict_maps_malformed_ai_response_to_502(client: TestClient) -> None:
    def malformed_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["not", "an", "object"])

    set_ai_response(client, malformed_response)
    response = client.post("/predict", json={"features": VALID_FEATURES})

    assert response.status_code == 502
    assert response.json()["error"] == "invalid_ai_response"


def test_health_reports_degraded_when_ai_is_unavailable(client: TestClient) -> None:
    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("service unavailable", request=request)

    set_ai_response(client, unavailable)
    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_cors_allows_local_frontend(client: TestClient) -> None:
    response = client.options(
        "/predict",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-request-id",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"