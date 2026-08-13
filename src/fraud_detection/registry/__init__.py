"""
ArtifactLoader with Singleton / LRU Caching to ensure model assets load once into memory.
"""
import json
from functools import lru_cache
from typing import Any, Dict

import joblib

from fraud_detection.artifacts import ArtifactManager
from fraud_detection.exceptions import ArtifactNotFoundError


class ArtifactLoader:
    """Loads champion model binaries, calibrators, preprocessors, and metadata assets once into memory."""

    def __init__(self, manager: ArtifactManager = None):
        self.manager = manager if manager else ArtifactManager()

    @lru_cache(maxsize=1)
    def load_assets(self) -> Dict[str, Any]:
        """Loads and caches all versioned binaries and JSON metadata."""
        try:
            model = joblib.load(self.manager.model_path)
            preprocessor = joblib.load(self.manager.preprocessor_path)
            calibrator = joblib.load(self.manager.calibrator_path)

            with open(self.manager.threshold_path, "r", encoding="utf-8") as f:
                threshold_data = json.load(f)

            with open(self.manager.metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            with open(self.manager.feature_schema_path, "r", encoding="utf-8") as f:
                feature_schema = json.load(f)

            with open(self.manager.feature_order_path, "r", encoding="utf-8") as f:
                feature_order = json.load(f)

            reference_priors = {}
            if hasattr(self.manager, "reference_priors_path") and self.manager.reference_priors_path.exists():
                with open(self.manager.reference_priors_path, "r", encoding="utf-8") as f:
                    reference_priors = json.load(f)

            raw_features = feature_schema.get("raw_features")
            if not raw_features:
                raw_features = [
                    "transaction_id", "Timestamp", "From_Account", "To_Account",
                    "From_Bank", "To_Bank", "Amount_Paid", "Amount_Received",
                    "Payment_Format", "Payment_Currency", "Receiving_Currency"
                ]

            return {
                "model": model,
                "preprocessor": preprocessor,
                "calibrator": calibrator,
                "optimal_threshold": float(threshold_data.get("optimal_threshold", 0.26)),
                "metadata": metadata,
                "feature_schema": feature_schema,
                "feature_order": feature_order,
                "reference_priors": reference_priors,
                "raw_features": raw_features
            }
        except Exception as e:
            raise ArtifactNotFoundError(f"Error loading versioned assets from registry: {str(e)}")
