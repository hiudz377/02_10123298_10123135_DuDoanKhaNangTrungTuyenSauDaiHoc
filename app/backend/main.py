"""REST API backend that validates admission features and calls the AI service."""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Optional
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, field_validator, model_validator


PORT = int(os.getenv("PORT", "8000"))
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:8001").rstrip("/")
AI_SERVICE_TIMEOUT = float(os.getenv("AI_SERVICE_TIMEOUT", "5"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
logger = logging.getLogger("backend")


class AdmissionFeatures(BaseModel):
    """Feature schema and basic domain validation for the admission dataset."""

    model_config = ConfigDict(extra="forbid")

    gre_score: StrictInt = Field(alias="GRE Score", ge=290, le=340)
    toefl_score: StrictInt = Field(alias="TOEFL Score", ge=92, le=120)
    university_rating: StrictInt = Field(alias="University Rating", ge=1, le=5)
    sop: StrictFloat = Field(alias="SOP", ge=1, le=5)
    lor: StrictFloat = Field(alias="LOR", ge=1, le=5)
    cgpa: StrictFloat = Field(alias="CGPA", ge=6.8, le=9.92)
    research: StrictInt = Field(alias="Research", ge=0, le=1)

    @field_validator("sop", "lor", mode="before")
    @classmethod
    def reject_bool_and_require_half_steps(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("must be a number")
        if not (float(value) * 2).is_integer():
            raise ValueError("must use half-point increments")
        return float(value)

    @field_validator("cgpa", mode="before")
    @classmethod
    def reject_non_numeric_cgpa(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("must be a number")
        return float(value)

    @model_validator(mode="after")
    def validate_finite_values(self) -> "AdmissionFeatures":
        if not all(
            map(
                lambda value: value == value and abs(value) != float("inf"),
                self.model_dump().values(),
            )
        ):
            raise ValueError("all feature values must be finite")
        return self


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: AdmissionFeatures
    request_id: Optional[str] = Field(default=None, min_length=1, max_length=128)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started_at = time.monotonic()
    app.state.ai_client = httpx.AsyncClient(timeout=AI_SERVICE_TIMEOUT)
    yield
    await app.state.ai_client.aclose()


app = FastAPI(
    title="Graduate Admission Backend",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID") or uuid4().hex
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            json.dumps(
                {
                    "event": "request_failed",
                    "request_id": request.state.request_id,
                    "method": request.method,
                    "path": request.url.path,
                }
            )
        )
        raise

    response.headers["X-Request-ID"] = request.state.request_id
    logger.info(
        json.dumps(
            {
                "event": "request_completed",
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            }
        )
    )
    return response


@app.exception_handler(RequestValidationError)
async def request_validation_error(request: Request, exc: RequestValidationError):
    details = [error["msg"] for error in exc.errors()]
    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_input",
            "detail": "; ".join(details),
            "request_id": request.state.request_id,
        },
    )


def error_response(request_id: str, status_code: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "detail": detail, "request_id": request_id},
    )


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    try:
        response = await request.app.state.ai_client.get(f"{AI_SERVICE_URL}/health")
        response.raise_for_status()
        ai_health = response.json()
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "port": PORT, "ai_service": "timeout"},
        )
    except (httpx.HTTPError, ValueError):
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "port": PORT, "ai_service": "unavailable"},
        )

    return JSONResponse(
        content={
            "status": "ok",
            "port": PORT,
            "uptime_seconds": round(time.monotonic() - request.app.state.started_at, 2),
            "ai_service": ai_health,
        }
    )


@app.post("/api/predict")
@app.post("/predict")
async def predict(payload: PredictRequest, request: Request) -> Any:
    request_id = payload.request_id or request.state.request_id
    request.state.request_id = request_id
    ai_payload = {
        "features": payload.features.model_dump(by_alias=True),
        "request_id": request_id,
    }

    try:
        response = await request.app.state.ai_client.post(
            f"{AI_SERVICE_URL}/predict",
            json=ai_payload,
            headers={"X-Request-ID": request_id},
        )
    except httpx.TimeoutException:
        return error_response(request_id, 504, "ai_service_timeout", "AI Service did not respond in time.")
    except httpx.HTTPError:
        return error_response(request_id, 503, "ai_service_unavailable", "AI Service is unavailable.")

    try:
        ai_result = response.json()
    except ValueError:
        return error_response(request_id, 502, "invalid_ai_response", "AI Service returned an invalid response.")
    if not isinstance(ai_result, dict):
        return error_response(request_id, 502, "invalid_ai_response", "AI Service returned an invalid response.")

    if response.status_code == 400 and ai_result.get("error") == "invalid_input":
        return error_response(
            request_id,
            400,
            "invalid_input",
            str(ai_result.get("detail", "AI Service rejected the input.")),
        )
    if response.is_error:
        return error_response(request_id, 502, "ai_service_error", "AI Service could not complete the prediction.")

    prediction = ai_result.get("prediction")
    if isinstance(prediction, bool) or not isinstance(prediction, (int, float)):
        return error_response(request_id, 502, "invalid_ai_response", "AI Service response is missing a numeric prediction.")

    return {
        "prediction": prediction,
        "chance_of_admit": prediction,
        "model_name": ai_result.get("model_name"),
        "model_version": ai_result.get("model_version"),
        "request_id": ai_result.get("request_id") or request_id,
    }