"""
Data Contracts and Type Definitions for Online Feature Engineering & Production Inference.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

import pandas as pd


@dataclass
class RawTransaction:
    """Represents a raw business transaction payload."""
    transaction_id: str
    Timestamp: str
    From_Account: str
    To_Account: str
    From_Bank: str
    To_Bank: str
    Amount_Paid: float
    Amount_Received: float
    Payment_Format: str
    Payment_Currency: str
    Receiving_Currency: str
    is_amount_outlier: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RawTransaction":
        return cls(
            transaction_id=str(data.get("transaction_id", data.get("transaction_key", "tx_001"))),
            Timestamp=str(data.get("Timestamp", "2026-08-06 12:00:00")),
            From_Account=str(data.get("From_Account", "acct_0")),
            To_Account=str(data.get("To_Account", "acct_1")),
            From_Bank=str(data.get("From_Bank", "10")),
            To_Bank=str(data.get("To_Bank", "20")),
            Amount_Paid=float(data.get("Amount_Paid", 0.0)),
            Amount_Received=float(data.get("Amount_Received", 0.0)),
            Payment_Format=str(data.get("Payment_Format", "ACH")),
            Payment_Currency=str(data.get("Payment_Currency", "USD")),
            Receiving_Currency=str(data.get("Receiving_Currency", "USD")),
            is_amount_outlier=float(data["is_amount_outlier"]) if "is_amount_outlier" in data and data["is_amount_outlier"] is not None else (1.0 if float(data.get("Amount_Paid", 0.0)) > 10000.0 else 0.0),
            extra=data
        )


@dataclass
class HistoricalContext:
    """Container holding historical context and reference priors for feature engineering."""
    sender_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    receiver_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    sender_stats: Dict[str, Any] = field(default_factory=dict)
    receiver_stats: Dict[str, Any] = field(default_factory=dict)
    reference_priors: Dict[str, Any] = field(default_factory=dict)
    is_cold_start_sender: bool = False
    is_cold_start_receiver: bool = False


@dataclass
class FeatureVector:
    """Container wrapping the engineered feature DataFrame ready for model preprocessing."""
    df: pd.DataFrame
    feature_count: int
    raw_transaction_id: str


@dataclass
class FeatureValidationResult:
    """Validation report tracking feature completeness, data types, NaNs, and ordering."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_features: List[str] = field(default_factory=list)
    nan_features: List[str] = field(default_factory=list)
