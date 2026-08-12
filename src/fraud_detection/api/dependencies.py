"""
FastAPI Dependencies for Enterprise Fraud Detection API.
"""
from typing import Optional
from fraud_detection.factories import EngineFactory
from fraud_detection.history import HistoryRepository
from fraud_detection.inference import PredictionEngine

_engine_instance: Optional[PredictionEngine] = None


def get_engine() -> PredictionEngine:
    """Dependency provider returning singleton PredictionEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        repo = HistoryRepository()
        _engine_instance = EngineFactory.create(history_repository=repo)
    return _engine_instance
