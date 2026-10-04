from __future__ import annotations

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, field_validator, model_validator
from pymongo import MongoClient

PORT = int(os.getenv("PORT", "8000"))
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:8001").rstrip("/")
AI_SERVICE_TIMEOUT = float(os.getenv("AI_SERVICE_TIMEOUT", "5"))

# Cấu hình MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "graduate_admission_db")

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
logger = logging.getLogger("backend")
logging.basicConfig(level=logging.INFO)


class AdmissionFeatures(BaseModel):
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
            raise ValueError("phải là một số")
        if not (float(value) * 2).is_integer():
            raise ValueError("phải dùng bước nhảy 0.5 (half-point)")
        return float(value)

    @field_validator("cgpa", mode="before")
    @classmethod
    def reject_non_numeric_cgpa(cls, value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("phải là một số")
        return float(value)

    @model_validator(mode="after")
    def validate_finite_values(self) -> "AdmissionFeatures":
        if not all(
            map(
                lambda value: value == value and abs(value) != float("inf"),
                self.model_dump().values(),
            )
        ):
            raise ValueError("tất cả các giá trị thuộc tính phải hữu hạn")
        return self


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: AdmissionFeatures
    request_id: Optional[str] = Field(default=None, min_length=1, max_length=128)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started_at = time.monotonic()
    app.state.ai_client = httpx.AsyncClient(timeout=AI_SERVICE_TIMEOUT)
    
    # Khởi tạo kết nối MongoDB
    try:
        app.state.mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        app.state.mongo_client.admin.command('ping')
        app.state.db = app.state.mongo_client[MONGO_DB_NAME]
        logger.info("Đã kết nối thành công tới cơ sở dữ liệu MongoDB.")
    except Exception as e:
        logger.warning(f"Không thể kết nối tới MongoDB: {e}")
        app.state.mongo_client = None
        app.state.db = None

    yield

    # Đóng kết nối khi tắt app
    if app.state.mongo_client:
        app.state.mongo_client.close()
        logger.info("Đã ngắt kết nối MongoDB.")
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
        duration = round((time.perf_counter() - started_at) * 1000, 2)
        logger.error(
            f"Request ID: {request.state.request_id} | Phương thức: {request.method} | Đường dẫn: {request.url.path} | Thời gian: {duration}ms"
        )
        raise

    duration = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        f"Request ID: {request.state.request_id} | Phương thức: {request.method} | Đường dẫn: {request.url.path} | Trạng thái: {response.status_code} | Thời gian: {duration}ms"
    )
    return response


@app.exception_handler(RequestValidationError)
async def request_validation_error(request: Request, exc: RequestValidationError):
    details = [error["msg"] for error in exc.errors()]
    error_message = "; ".join(details)
    logger.warning(f"Request ID: {request.state.request_id} | Lỗi: {error_message}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_input",
            "detail": error_message,
            "request_id": request.state.request_id,
        },
    )


def error_response(request_id: str, status_code: int, error: str, detail: str) -> JSONResponse:
    logger.error(f"Request ID: {request_id} | Mã: {status_code} | Lỗi: {error} | Chi tiết: {detail}")
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

    db_status = "unavailable"
    if request.app.state.mongo_client:
        try:
            request.app.state.mongo_client.admin.command('ping')
            db_status = "ok"
        except Exception:
            db_status = "error"

    return JSONResponse(
        content={
            "status": "ok",
            "port": PORT,
            "uptime_seconds": round(time.monotonic() - request.app.state.started_at, 2),
            "ai_service": ai_health,
            "database": db_status,
        }
    )


@app.get("/api/history")
@app.get("/history")
async def get_prediction_history(request: Request, limit: int = 10) -> Any:
    db = getattr(request.app.state, "db", None)
    if db is None:
        return error_response(request.state.request_id, 503, "database_unavailable", "Không thể kết nối cơ sở dữ liệu.")
    
    try:
        history_cursor = db["prediction_history"].find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
        history_list = list(history_cursor)
        logger.info(f"Đã truy xuất thành công {len(history_list)} bản ghi lịch sử dự đoán.")
        return {"history": history_list}
    except Exception as e:
        logger.error(f"Không thể lấy lịch sử từ MongoDB: {e}")
        return error_response(request.state.request_id, 500, "database_error", "Không thể truy xuất lịch sử dự đoán.")


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
        return error_response(request_id, 504, "ai_service_timeout", "AI Service phản hồi quá thời gian quy định.")
    except httpx.HTTPError:
        return error_response(request_id, 503, "ai_service_unavailable", "Dịch vụ AI hiện không khả dụng.")

    try:
        ai_result = response.json()
    except ValueError:
        return error_response(request_id, 502, "invalid_ai_response", "Dịch vụ AI trả về phản hồi không hợp lệ.")
    
    if not isinstance(ai_result, dict):
        return error_response(request_id, 502, "invalid_ai_response", "Dịch vụ AI trả về phản hồi không đúng định dạng.")

    if response.status_code == 400 and ai_result.get("error") == "invalid_input":
        return error_response(
            request_id,
            400,
            "invalid_input",
            str(ai_result.get("detail", "Dịch vụ AI đã từ chối dữ liệu đầu vào.")),
        )
    if response.is_error:
        return error_response(request_id, 502, "ai_service_error", "Dịch vụ AI gặp lỗi khi thực hiện dự đoán.")

    prediction = ai_result.get("prediction")
    if isinstance(prediction, bool) or not isinstance(prediction, (int, float)):
        return error_response(request_id, 502, "invalid_ai_response", "Phản hồi từ AI thiếu giá trị dự đoán dạng số.")

    result_data = {
        "prediction": prediction,
        "chance_of_admit": prediction,
        "model_name": ai_result.get("model_name"),
        "model_version": ai_result.get("model_version"),
        "request_id": ai_result.get("request_id") or request_id,
    }

    # Lưu lịch sử vào MongoDB
    db = getattr(request.app.state, "db", None)
    if db is not None:
        try:
            history_doc = {
                "request_id": result_data["request_id"],
                "features": payload.features.model_dump(by_alias=True),
                "prediction_result": result_data,
                "created_at": datetime.now(timezone.utc),
            }
            db["prediction_history"].insert_one(history_doc)
            logger.info(f"Đã lưu lịch sử dự đoán thành công cho Request ID: {result_data['request_id']}")
        except Exception as e:
            logger.error(f"Không thể lưu lịch sử vào MongoDB: {e}")

    return result_data