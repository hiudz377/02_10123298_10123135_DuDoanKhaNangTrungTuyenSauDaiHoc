"""FastAPI service for graduate-admission chance regression models."""

from __future__ import annotations

import json
import logging
import math
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import joblib
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


AI_MODELS_ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.getenv("PORT", "8001"))
FEATURES = [
	"GRE Score",
	"TOEFL Score",
	"University Rating",
	"SOP",
	"LOR",
	"CGPA",
	"Research",
]
TARGET = "Chance of Admit"
FEATURE_RANGES = {
	"GRE Score": (290.0, 340.0),
	"TOEFL Score": (92.0, 120.0),
	"University Rating": (1.0, 5.0),
	"SOP": (1.0, 5.0),
	"LOR": (1.0, 5.0),
	"CGPA": (6.8, 9.92),
	"Research": (0.0, 1.0),
}
INTEGER_FEATURES = {"GRE Score", "TOEFL Score", "University Rating", "Research"}
logger = logging.getLogger("ai-service")


class PredictRequest(BaseModel):
	model_config = ConfigDict(extra="forbid")

	features: dict[str, Any]
	request_id: Optional[str] = Field(default=None, max_length=128)


def _resolve_path(value: str) -> Path:
	path = Path(value)
	return path if path.is_absolute() else AI_MODELS_ROOT / path


def _load_model() -> tuple[Any, dict[str, Any]]:
	artifact_path = _resolve_path(
		os.getenv("MODEL_PATH", "models/graduate_admission_model.joblib")
	)
	if not artifact_path.is_file():
		raise FileNotFoundError(f"Model artifact does not exist: {artifact_path}")

	model = joblib.load(artifact_path)
	if not callable(getattr(model, "predict", None)):
		raise TypeError("The configured model artifact does not provide predict().")

	model_features = list(getattr(model, "feature_names_in_", FEATURES))
	if model_features != FEATURES or getattr(model, "n_features_in_", None) != len(FEATURES):
		raise ValueError(f"Model must use these ordered features: {FEATURES}")

	configured_metadata = os.getenv("MODEL_METADATA_PATH")
	metadata_path = (
		_resolve_path(configured_metadata)
		if configured_metadata
		else artifact_path.with_name(f"{artifact_path.stem}_metadata.json")
	)
	metadata = (
		json.loads(metadata_path.read_text(encoding="utf-8"))
		if metadata_path.is_file()
		else {}
	)
	if metadata.get("features", FEATURES) != FEATURES:
		raise ValueError("Model metadata feature order does not match the service schema.")

	default_names = {
		"graduate_admission_model": "Linear Regression",
		"knn_regressor_personal": "KNN",
		"svr_regressor_personal": "SVR",
	}
	info = {
		"model_name": metadata.get(
			"model_name", default_names.get(artifact_path.stem, artifact_path.stem)
		),
		"model_version": metadata.get("model_version", os.getenv("MODEL_VERSION", "1.0.0")),
		"artifact": artifact_path.name,
		"target": metadata.get("target", TARGET),
		"features": FEATURES,
		"test_metrics": metadata.get("test_metrics"),
		"best_parameters": metadata.get("best_parameters"),
		"versions": metadata.get("versions"),
	}
	return model, info


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Load and validate the artifact once when the service starts."""
	app.state.model, app.state.model_info = _load_model()
	app.state.started_at = time.monotonic()
	logger.info(
		json.dumps(
			{
				"event": "model_loaded",
				"model": app.state.model_info["model_name"],
				"artifact": app.state.model_info["artifact"],
				"model_version": app.state.model_info["model_version"],
			}
		)
	)
	yield


app = FastAPI(
	title="Graduate Admission AI Service",
	version="1.0.0",
	lifespan=lifespan,
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


def _invalid_input(request_id: str, detail: str) -> JSONResponse:
	return JSONResponse(
		status_code=400,
		content={"error": "invalid_input", "detail": detail, "request_id": request_id},
	)


def _validate_features(
	features: dict[str, Any],
) -> tuple[Optional[list[float]], Optional[str]]:
	missing = [name for name in FEATURES if name not in features]
	extra = [name for name in features if name not in FEATURES]
	if missing or extra:
		parts = []
		if missing:
			parts.append(f"Missing features: {', '.join(missing)}")
		if extra:
			parts.append(f"Unexpected features: {', '.join(extra)}")
		return None, "; ".join(parts)

	values = []
	for name in FEATURES:
		value = features[name]
		if isinstance(value, bool) or not isinstance(value, (int, float)):
			return None, f"{name} must be a number."

		number = float(value)
		minimum, maximum = FEATURE_RANGES[name]
		if not math.isfinite(number) or not minimum <= number <= maximum:
			return None, f"{name} must be between {minimum:g} and {maximum:g}."
		if name in INTEGER_FEATURES and not number.is_integer():
			return None, f"{name} must be an integer."
		if name in {"SOP", "LOR"} and not math.isclose(number * 2, round(number * 2)):
			return None, f"{name} must use half-point increments."
		values.append(number)
	return values, None


@app.get("/health")
async def health(request: Request) -> dict[str, Any]:
	return {
		"status": "ok",
		"port": PORT,
		"uptime_seconds": round(time.monotonic() - request.app.state.started_at, 2),
		"model_loaded": request.app.state.model is not None,
	}


@app.get("/model-info")
async def model_info(request: Request) -> dict[str, Any]:
	return request.app.state.model_info


@app.post("/predict")
async def predict(payload: PredictRequest, request: Request) -> Any:
	request_id = payload.request_id or request.state.request_id
	request.state.request_id = request_id
	values, error = _validate_features(payload.features)
	if error:
		return _invalid_input(request_id, error)

	feature_frame = pd.DataFrame([values], columns=FEATURES)
	started_at = time.perf_counter()
	prediction = float(request.app.state.model.predict(feature_frame)[0])
	logger.info(
		json.dumps(
			{
				"event": "prediction_completed",
				"request_id": request_id,
				"model": request.app.state.model_info["model_name"],
				"prediction": prediction,
				"duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
			}
		)
	)
	return {
		"prediction": prediction,
		"model_name": request.app.state.model_info["model_name"],
		"model_version": request.app.state.model_info["model_version"],
		"request_id": request_id,
	}
