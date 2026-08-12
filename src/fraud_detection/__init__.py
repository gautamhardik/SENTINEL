"""
Enterprise Fraud Detection Package.
Provides production inference, artifact loading, probability calibration, risk thresholding, explainability, and governance.
"""

__version__ = "1.0.0"
__author__ = "Lead AI/ML Engineering Team"

from fraud_detection.factories import EngineFactory
from fraud_detection.history import HistoryRepository, HistoryWriter
from fraud_detection.inference import PredictionEngine

__all__ = ["EngineFactory", "HistoryRepository", "HistoryWriter", "PredictionEngine", "__version__"]
