"""
Production FastAPI Inference Application for Enterprise Fraud Detection Engine.
Exposes clean, versioned endpoints for health checks, readiness probes, model metadata, and single/batch transaction predictions.
"""
from contextlib import asynccontextmanager
import time
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd

from fraud_detection.factories import EngineFactory
from fraud_detection.history import HistoryRepository
from fraud_detection.inference import PredictionEngine
from fraud_detection.exceptions import (
    ArtifactNotFoundError,
    CalibrationError,
    ConfigurationError,
    FeatureValidationError,
    FraudDetectionBaseException,
    PredictionEngineError,
    SchemaMismatchError,
)
from fraud_detection.api.schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    HealthResponse,
    ModelInfoResponse,
    PredictionRequest,
    PredictionResponse,
    ReadinessResponse,
)

# Global singleton engine instance initialized during lifespan startup
_engine: Optional[PredictionEngine] = None
_start_time: float = time.time()
_prediction_counter: int = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager to initialize and warm up model assets once at startup."""
    from fraud_detection.api import dependencies
    repo = HistoryRepository()
    engine = EngineFactory.create(history_repository=repo)
    engine.warmup()
    dependencies._engine_instance = engine
    yield
    dependencies._engine_instance = None


app = FastAPI(
    title="Enterprise Fraud Detection Engine API",
    description="Production-grade real-time fraud detection and risk scoring service powered by Optuna-Tuned LightGBM and Isotonic Calibration.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS middleware with environment-driven allowed origins
import os
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fraud_detection.api.dependencies import get_engine


# ================= Middleware for Request ID & Headers =================

import uuid

@app.middleware("http")
async def add_request_metadata(request: Request, call_next):
    """Middleware attaching request IDs and model metadata headers."""
    req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
    start = time.time()
    response: Response = await call_next(request)
    latency_ms = round((time.time() - start) * 1000, 2)
    response.headers["X-Model-Version"] = "1.0.0"
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time-Ms"] = str(latency_ms)
    return response


# ================= Global Exception Handlers =================

from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    cleaned_details = []
    for err in exc.errors():
        cleaned_details.append({
            "loc": [str(loc_item) for loc_item in err.get("loc", [])],
            "msg": str(err.get("msg", "")),
            "type": str(err.get("type", ""))
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid transaction payload",
                "details": cleaned_details
            }
        }
    )


@app.exception_handler(FeatureValidationError)
async def feature_validation_exception_handler(request: Request, exc: FeatureValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "title": "Feature Validation Error",
                "message": str(exc),
                "timestamp": pd.Timestamp.now().isoformat()
            }
        }
    )


@app.exception_handler(ArtifactNotFoundError)
async def artifact_not_found_exception_handler(request: Request, exc: ArtifactNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": {
                "code": "SERVICE_UNAVAILABLE",
                "title": "Model Registry Service Unavailable",
                "message": str(exc),
                "timestamp": pd.Timestamp.now().isoformat()
            }
        }
    )


@app.exception_handler(ConfigurationError)
async def configuration_exception_handler(request: Request, exc: ConfigurationError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "CONFIG_ERROR",
                "title": "System Configuration Error",
                "message": str(exc),
                "timestamp": pd.Timestamp.now().isoformat()
            }
        }
    )


@app.exception_handler(FraudDetectionBaseException)
async def general_fraud_exception_handler(request: Request, exc: FraudDetectionBaseException):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INFERENCE_ERROR",
                "title": "Inference Execution Error",
                "message": str(exc),
                "timestamp": pd.Timestamp.now().isoformat()
            }
        }
    )


# ================= Health & Operational Endpoints =================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check(response: Response):
    """Liveness probe returning server health status."""
    response.headers["X-Model-Version"] = "1.0.0"
    return HealthResponse(
        status="healthy",
        timestamp=pd.Timestamp.now().isoformat()
    )



@app.get("/ready", response_model=ReadinessResponse, tags=["Health"])
@app.get("/health/ready", response_model=ReadinessResponse, tags=["Health"])
def readiness_probe(response: Response, engine: PredictionEngine = Depends(get_engine)):
    """Readiness probe checking model loading, feature store connectivity, and memory status."""
    is_ready = engine is not None and hasattr(engine, "service")
    db_connected = False
    if is_ready and engine.service.online_feature_service:
        try:
            repo = engine.service.online_feature_service.context_service.repository
            db_connected = True if getattr(repo, "in_memory", False) else (repo.db.connect() is not None)
        except Exception:
            db_connected = False

    ready = is_ready and db_connected
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        model_loaded=is_ready,
        database_ready=db_connected,
        registry_active=True
    )


@app.get("/metrics", tags=["Operational"])
def get_metrics():
    """Operational metrics endpoint returning server uptime and prediction count."""
    return {
        "uptime_seconds": round(time.time() - _start_time, 2),
        "total_predictions": _prediction_counter,
        "status": "healthy"
    }


@app.get("/api/v1/model/info", response_model=ModelInfoResponse, tags=["Metadata"])
@app.get("/api/v1/model", tags=["Metadata"])
def get_model_info(engine: PredictionEngine = Depends(get_engine)):
    """Exposes safe model metadata and configuration parameters."""
    svc = engine.service
    thresh = getattr(svc.threshold_engine, "optimal_threshold", 0.2556561085972851)
    return ModelInfoResponse(
        model_name=svc.metadata.get("model_name", "Optuna-Tuned LightGBM"),
        algorithm="LGBMClassifier",
        model_version=svc.metadata.get("version", "v1.0.0"),
        feature_count=len(svc.feature_order),
        calibration_method="Isotonic Regression",
        threshold=thresh,
        supported_api_version="1.0.0"
    )


@app.get("/api/v1/features", tags=["Metadata"])
def get_feature_store_info(engine: PredictionEngine = Depends(get_engine)):
    """Exposes feature counts for raw inputs and preprocessed model features."""
    raw_cnt = len(engine.service.raw_features) if hasattr(engine.service, "raw_features") and engine.service.raw_features else 11
    return {
        "raw_feature_count": raw_cnt,
        "processed_feature_count": len(engine.service.feature_order)
    }


@app.get("/api/v1/version", tags=["Metadata"])
@app.get("/api/v1/info", tags=["Metadata"])
def get_version_info():
    """Returns package and API version details."""
    return {
        "package_version": "1.0.0",
        "api_version": "1.0.0"
    }


# ================= Inference Endpoints =================

@app.post("/api/v1/predict", response_model=PredictionResponse, tags=["Inference"])
def predict_single_transaction(
    payload: PredictionRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    engine: PredictionEngine = Depends(get_engine)
):
    """
    Executes real-time fraud inference for a single raw transaction payload.
    Automatically handles backend is_amount_outlier derivation and persistent account state updates.
    """
    global _prediction_counter
    _prediction_counter += 1

    # Convert request payload to dictionary representation
    raw_dict = payload.to_raw_dict()

    # Call production prediction engine
    try:
        session = engine.predict(raw_dict)
    except (FeatureValidationError, ArtifactNotFoundError, ConfigurationError, FraudDetectionBaseException):
        raise
    except Exception as e:
        err_msg = str(e)
        if "PostgreSQL" in err_msg or "database" in err_msg.lower() or "connection" in err_msg.lower():
            logger.error(f"Database connection failure during prediction: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable. Ensure PostgreSQL database container is running or DB_ENGINE_TYPE is configured correctly."
            )
        logger.error(f"Unhandled prediction pipeline exception: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Inference pipeline execution error: {err_msg}")


    # Map PredictionSession into clean PredictionResponse
    top_drivers = session.top_risk_drivers if isinstance(session.top_risk_drivers, list) else []
    
    # Map decision to recommended action
    action_map = {
        "APPROVED_LEGITIMATE": "APPROVE",
        "APPROVED_WITH_MONITORING": "MONITOR",
        "FLAGGED_FRAUD": "HOLD_FOR_MANUAL_INVESTIGATION",
        "FLAGGED_CRITICAL_FRAUD": "DECLINE_IMMEDIATELY"
    }
    rec_action = action_map.get(session.decision, "HOLD_FOR_MANUAL_INVESTIGATION")

    return PredictionResponse(
        transaction_id=payload.transaction_id,
        request_id=session.request_id,
        decision=session.decision,
        risk_level=session.risk_level.value if hasattr(session.risk_level, "value") else str(session.risk_level),
        calibrated_probability=round(session.calibrated_probability, 6),
        fraud_probability=round(session.calibrated_probability, 6),
        raw_probability=round(session.raw_probability, 6),
        threshold=round(session.threshold, 6),
        recommended_action=rec_action,
        explanation={
            "top_risk_drivers": top_drivers,
            "investigator_card": session.investigator_card
        },
        inference_latency_ms=round(session.total_latency_ms, 2),
        model_version=session.model_version,
        timestamp=session.timestamp
    )


@app.post("/api/v1/predict/batch", response_model=BatchPredictionResponse, tags=["Inference"])
def predict_batch_transactions(
    payload: BatchPredictionRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    engine: PredictionEngine = Depends(get_engine)
):
    """
    Executes vectorized batch fraud inference for multiple raw transaction payloads.
    """
    global _prediction_counter
    start_time = time.time()
    
    raw_dicts = [tx.to_raw_dict() for tx in payload.transactions]
    df_raw = pd.DataFrame(raw_dicts)
    _prediction_counter += len(raw_dicts)

    try:
        sessions = engine.predict_batch(df_raw, include_explanations=payload.include_explanations)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Batch inference failed: {str(e)}")

    responses = []
    action_map = {
        "APPROVED_LEGITIMATE": "APPROVE",
        "APPROVED_WITH_MONITORING": "MONITOR",
        "FLAGGED_FRAUD": "HOLD_FOR_MANUAL_INVESTIGATION",
        "FLAGGED_CRITICAL_FRAUD": "DECLINE_IMMEDIATELY"
    }

    for tx_req, s in zip(payload.transactions, sessions):
        rec_action = action_map.get(s.decision, "HOLD_FOR_MANUAL_INVESTIGATION")
        responses.append(
            PredictionResponse(
                transaction_id=tx_req.transaction_id,
                request_id=s.request_id,
                decision=s.decision,
                risk_level=s.risk_level.value if hasattr(s.risk_level, "value") else str(s.risk_level),
                calibrated_probability=round(s.calibrated_probability, 6),
                fraud_probability=round(s.calibrated_probability, 6),
                raw_probability=round(s.raw_probability, 6),
                threshold=round(s.threshold, 6),
                recommended_action=rec_action,
                explanation={
                    "top_risk_drivers": s.top_risk_drivers if isinstance(s.top_risk_drivers, list) else [],
                    "investigator_card": s.investigator_card
                },
                inference_latency_ms=round(s.total_latency_ms, 2),
                model_version=s.model_version,
                timestamp=s.timestamp
            )
        )

    total_latency = round((time.time() - start_time) * 1000, 2)
    return BatchPredictionResponse(
        processed=len(responses),
        successful=len(responses),
        predictions=responses,
        batch_latency_ms=total_latency
    )
