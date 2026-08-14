"""
Pydantic Request and Response Schemas for Production Fraud Detection API.
"""
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field, field_validator


class PredictionRequest(BaseModel):
    """Clean public API request schema expecting ONLY the 11 raw transaction fields."""
    transaction_id: str = Field(..., description="Unique transaction correlation identifier", json_schema_extra={"example": "TX-99812"})
    Timestamp: str = Field(..., description="Transaction timestamp in ISO or standard format", json_schema_extra={"example": "2026-08-11T14:15:00"})
    From_Account: str = Field(..., description="Sender account identifier", json_schema_extra={"example": "ACC_1029"})
    To_Account: str = Field(..., description="Receiver account identifier", json_schema_extra={"example": "ACC_8841"})
    From_Bank: str = Field(..., description="Sender bank identifier", json_schema_extra={"example": "BANK_12"})
    To_Bank: str = Field(..., description="Receiver bank identifier", json_schema_extra={"example": "BANK_45"})
    Amount_Paid: float = Field(..., gt=0.0, description="Amount sent in transaction currency", json_schema_extra={"example": 12500.0})
    Amount_Received: float = Field(..., gt=0.0, description="Amount received in receiving currency", json_schema_extra={"example": 12500.0})
    Payment_Format: str = Field("ACH", description="Payment format / method", json_schema_extra={"example": "Wire"})
    Payment_Currency: str = Field("USD", description="Currency sent", json_schema_extra={"example": "USD"})
    Receiving_Currency: str = Field("USD", description="Currency received", json_schema_extra={"example": "USD"})

    @field_validator("From_Account", "To_Account", "From_Bank", "To_Bank", "transaction_id")
    @classmethod
    def non_empty_string(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must be a non-empty string")
        return v.strip()

    @field_validator("Payment_Format")
    @classmethod
    def validate_payment_format(cls, v: str) -> str:
        allowed: Set[str] = {"Wire Transfer", "ACH Outbound", "Cheque", "Credit Card", "Cash Deposit"}
        if v not in allowed:
            raise ValueError(
                f"Invalid Payment_Format '{v}'. Allowed values: {sorted(allowed)}"
            )
        return v

    @field_validator("Payment_Currency", "Receiving_Currency")
    @classmethod
    def validate_currency(cls, v: str, info) -> str:
        allowed: Set[str] = {"USD", "EUR", "GBP", "CAD", "AUD"}
        if v not in allowed:
            raise ValueError(
                f"Invalid {info.field_name} '{v}'. Allowed values: {sorted(allowed)}"
            )
        return v

    @field_validator("Timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("Timestamp must be a non-empty string")
        try:
            import pandas as pd
            parsed = pd.to_datetime(v)
            if pd.isna(parsed):
                raise ValueError(f"Invalid timestamp format: '{v}'")
        except Exception:
            raise ValueError(f"Invalid timestamp format: '{v}'")
        return v.strip()

    def to_raw_dict(self) -> Dict[str, Any]:
        """Converts pydantic model to dictionary representation for RawTransaction.from_dict."""
        return {
            "transaction_id": self.transaction_id,
            "Timestamp": self.Timestamp,
            "From_Account": self.From_Account,
            "To_Account": self.To_Account,
            "From_Bank": self.From_Bank,
            "To_Bank": self.To_Bank,
            "Amount_Paid": self.Amount_Paid,
            "Amount_Received": self.Amount_Received,
            "Payment_Format": self.Payment_Format,
            "Payment_Currency": self.Payment_Currency,
            "Receiving_Currency": self.Receiving_Currency
        }


class BatchPredictionRequest(BaseModel):
    """Vectorized batch prediction request payload."""
    transactions: List[PredictionRequest] = Field(..., min_length=1, max_length=500, description="List of raw transaction payloads")
    include_explanations: bool = Field(True, description="Whether to include full SHAP explanation cards for each transaction")


class HealthResponse(BaseModel):
    """Liveness probe response model."""
    status: str = Field("healthy", json_schema_extra={"example": "healthy"})
    timestamp: str = Field(..., json_schema_extra={"example": "2026-08-11T23:00:00"})


class ReadinessResponse(BaseModel):
    """Readiness probe response model checking serving dependencies."""
    status: str = Field("ready", json_schema_extra={"example": "ready"})
    model_loaded: bool = Field(True, json_schema_extra={"example": True})
    database_ready: bool = Field(True, json_schema_extra={"example": True})
    registry_active: bool = Field(True, json_schema_extra={"example": True})


class ModelInfoResponse(BaseModel):
    """Metadata response model describing active model version and threshold."""
    model_name: str = Field(..., json_schema_extra={"example": "Optuna-Tuned LightGBM Classifier"})
    algorithm: str = Field(..., json_schema_extra={"example": "LGBMClassifier"})
    model_version: str = Field(..., json_schema_extra={"example": "v1.0.0"})
    feature_count: int = Field(61, json_schema_extra={"example": 61})
    calibration_method: str = Field(..., json_schema_extra={"example": "Isotonic Regression"})
    threshold: float = Field(0.2556561085972851, json_schema_extra={"example": 0.255656})
    supported_api_version: str = Field("1.0.0", json_schema_extra={"example": "1.0.0"})


class PredictionResponse(BaseModel):
    """Stable public prediction response schema exposing calibrated probability and SHAP explanations."""
    transaction_id: str = Field(..., json_schema_extra={"example": "TX-99812"})
    request_id: str = Field(..., json_schema_extra={"example": "req_84920a"})
    decision: str = Field(..., json_schema_extra={"example": "FLAGGED_FRAUD"})
    risk_level: str = Field(..., json_schema_extra={"example": "HIGH"})
    calibrated_probability: float = Field(..., json_schema_extra={"example": 0.31845})
    fraud_probability: float = Field(..., json_schema_extra={"example": 0.31845})
    raw_probability: float = Field(..., json_schema_extra={"example": 0.29100})
    threshold: float = Field(0.2556561085972851, json_schema_extra={"example": 0.255656})
    recommended_action: str = Field(..., json_schema_extra={"example": "HOLD_FOR_MANUAL_INVESTIGATION"})
    explanation: Dict[str, Any] = Field(..., description="Top risk drivers and Markdown investigator decision card")
    inference_latency_ms: float = Field(..., json_schema_extra={"example": 18.42})
    model_version: str = Field("v1.0.0", json_schema_extra={"example": "v1.0.0"})
    timestamp: str = Field(..., json_schema_extra={"example": "2026-08-11T14:15:00"})


class BatchPredictionResponse(BaseModel):
    """Vectorized batch prediction response schema."""
    processed: int = Field(..., json_schema_extra={"example": 2})
    successful: int = Field(..., json_schema_extra={"example": 2})
    predictions: List[PredictionResponse]
    batch_latency_ms: float = Field(..., json_schema_extra={"example": 34.12})
