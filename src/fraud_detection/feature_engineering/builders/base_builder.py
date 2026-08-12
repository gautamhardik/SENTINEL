"""
Base feature builder abstract interface.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict

from fraud_detection.core.contracts import HistoricalContext, RawTransaction


class BaseFeatureBuilder(ABC):
    """Abstract interface for modular feature group builders."""

    @abstractmethod
    def build(self, transaction: RawTransaction, context: HistoricalContext) -> Dict[str, Any]:
        """Calculates and returns a dictionary of features for the given transaction and historical context."""
        pass
