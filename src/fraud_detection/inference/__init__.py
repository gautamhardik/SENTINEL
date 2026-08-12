"""
PredictionEngine Facade Module serving as the primary entrypoint for the fraud_detection package.
Exposes simple, high-level predict() and predict_batch() methods with comprehensive docstrings and usage examples.
"""
from typing import List, Optional, Union

import pandas as pd

from fraud_detection.core import PredictionSession
from fraud_detection.services import PredictionService


class PredictionEngine:
    """
    Lightweight facade wrapping PredictionService for real-time and batch fraud inference.

    Examples
    --------
    >>> from fraud_detection import EngineFactory
    >>> engine = EngineFactory.create()
    >>> transaction = {
    ...     "Amount_Paid": 500.0,
    ...     "Amount_Received": 500.0,
    ...     "is_amount_outlier": 0.0,
    ...     # ... other 75 raw features
    ... }
    >>> response = engine.predict(transaction)
    >>> print(response.decision, response.calibrated_probability, response.risk_level)
    APPROVED_LEGITIMATE 0.0452 RiskLevel.LOW
    """

    def __init__(self, service: PredictionService):
        """
        Parameters
        ----------
        service : PredictionService
            Wired prediction service instance orchestrating pipeline stages.
        """
        self.service = service

    def predict(self, transaction: Union[pd.DataFrame, dict]) -> PredictionSession:
        """
        Executes real-time single-transaction fraud inference.

        Parameters
        ----------
        transaction : Union[pd.DataFrame, dict]
            Single transaction payload as a pandas DataFrame (1 row) or a dictionary mapping feature names to values.

        Returns
        -------
        PredictionSession
            Structured prediction response containing request ID, decision, risk level,
            calibrated probability, top SHAP risk drivers, actionable recourse advice, and stage latencies.

        Examples
        --------
        >>> session = engine.predict(raw_tx_df)
        >>> print(session.decision)
        'APPROVED_WITH_MONITORING'
        """
        if isinstance(transaction, dict):
            df = pd.DataFrame([transaction])
        else:
            df = transaction
        return self.service.predict_single(df)

    def predict_batch(self, transactions: Union[pd.DataFrame, List[dict]], include_explanations: bool = True) -> List[PredictionSession]:
        """
        Executes vectorized batch-transaction fraud inference over multiple transactions.

        Parameters
        ----------
        transactions : Union[pd.DataFrame, List[dict]]
            Batch transaction payload as a pandas DataFrame or list of dictionaries.
        include_explanations : bool, default=True
            Whether to compute full SHAP TreeExplainer local feature attributions for each transaction in the batch.

        Returns
        -------
        List[PredictionSession]
            List of structured prediction responses matching input order.

        Examples
        --------
        >>> sessions = engine.predict_batch(batch_df, include_explanations=False)
        >>> print(len(sessions))
        1000
        """
        if isinstance(transactions, list):
            df = pd.DataFrame(transactions)
        else:
            df = transactions
        return self.service.predict_batch(df, include_explanations=include_explanations)

    def warmup(self) -> bool:
        """Executes a harmless dummy scoring warmup to load C++ native LightGBM libraries without mutating persistent state."""
        try:
            import numpy as np
            dummy_matrix = np.zeros((1, len(self.service.feature_order)), dtype=np.float64)
            raw_model = self.service.model.estimator if hasattr(self.service.model, "estimator") else self.service.model
            if hasattr(raw_model, "predict_proba"):
                _ = raw_model.predict_proba(dummy_matrix)
            if hasattr(self.service.calibrator, "calibrate"):
                _ = self.service.calibrator.calibrate(np.array([0.1]))
            return True
        except Exception:
            return False

