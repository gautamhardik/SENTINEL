"""
Core enums, constants, types, and abstract protocol interfaces for fraud_detection package.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import numpy as np
import pandas as pd

from fraud_detection.core.contracts import FeatureValidationResult, FeatureVector, HistoricalContext, RawTransaction


class RiskLevel(str, Enum):
    """Business risk levels based on calibrated probability thresholding."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ModelStatus(str, Enum):
    """Model registry deployment status."""
    CHAMPION = "CHAMPION"
    CHALLENGER = "CHALLENGER"
    ARCHIVED = "ARCHIVED"


class CalibrationMethod(str, Enum):
    """Supported probability calibration algorithms."""
    ISOTONIC = "isotonic"
    PLATT = "sigmoid"


@dataclass(frozen=True)
class PredictionContext:
    """Immutable context carried through each inference request."""
    request_id: str
    model_name: str
    model_version: str
    optimal_threshold: float
    start_time: float
    feature_count: int


@dataclass
class ValidationResult:
    """Output summary of feature validation check."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    passed_count: int = 0


@dataclass
class RiskResult:
    """Output summary of threshold engine risk classification."""
    decision: str
    risk_level: RiskLevel
    threshold: float
    action: str
    trigger_reason: str


@dataclass
class BusinessExplanation:
    """Human-readable business explanation for investigator review."""
    investigator_card: str
    top_risk_drivers: List[Dict[str, Any]]
    counterfactual_advice: List[Dict[str, Any]]


@dataclass
class PredictionSession:
    """Structured response container returned by PredictionEngine."""
    request_id: str
    decision: str
    risk_level: RiskLevel
    raw_probability: float
    calibrated_probability: float
    threshold: float
    top_risk_drivers: List[Dict[str, Any]]
    counterfactual_advice: List[Dict[str, Any]]
    investigator_card: str
    model_version: str
    total_latency_ms: float
    stage_latencies_ms: Dict[str, float]
    timestamp: str

    @property
    def explanation(self) -> "PredictionSession":
        """Backward-compatibility wrapper returning self for .explanation accesses."""
        return self


# ================= Protocol Interfaces =================

@runtime_checkable
class BaseValidator(Protocol):
    def validate(self, df: pd.DataFrame) -> ValidationResult: ...

@runtime_checkable
class BaseLoader(Protocol):
    def load_assets(self) -> Dict[str, Any]: ...

@runtime_checkable
class BaseCalibrator(Protocol):
    def calibrate(self, raw_probs: np.ndarray) -> np.ndarray: ...

@runtime_checkable
class BaseThresholdEngine(Protocol):
    def evaluate(self, calibrated_prob: float) -> RiskResult: ...

@runtime_checkable
class BaseExplainer(Protocol):
    def explain(self, sample_row: np.ndarray, shap_row: np.ndarray, proba: float, threshold: float) -> BusinessExplanation: ...
