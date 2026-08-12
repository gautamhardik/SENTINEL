"""
OnlineFeatureService orchestrating context retrieval, feature group building, feature assembly, and dynamic schema ordering.
"""
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from fraud_detection.core.contracts import RawTransaction
from fraud_detection.exceptions import FeatureValidationError
from fraud_detection.feature_engineering.feature_registry import FeatureRegistry
from fraud_detection.retrieval.context_service import ContextService


class OnlineFeatureService:
    """Orchestrates historical context retrieval and online feature engineering for inference."""

    def __init__(
        self,
        context_service: ContextService,
        feature_order: List[str],
        registry: Optional[FeatureRegistry] = None
    ):
        self.context_service = context_service
        self.feature_order = list(feature_order)
        self.registry = registry or FeatureRegistry()

    def build_features_single(self, raw_tx_input: Union[RawTransaction, Dict[str, Any]]) -> pd.DataFrame:
        """Builds ordered 61-feature DataFrame for a single raw transaction."""
        if isinstance(raw_tx_input, dict):
            raw_tx = RawTransaction.from_dict(raw_tx_input)
        else:
            raw_tx = raw_tx_input

        context = self.context_service.get_context_for_transaction(raw_tx)

        feature_dict: Dict[str, Any] = {}
        for builder in self.registry.get_builders():
            group_feats = builder.build(raw_tx, context)
            feature_dict.update(group_feats)

        # Assemble and reorder DataFrame strictly matching feature_order
        assembled_df = self._assemble_and_align_dataframe([feature_dict])
        return assembled_df

    def build_features_batch(self, raw_tx_inputs: Union[List[Dict[str, Any]], pd.DataFrame]) -> pd.DataFrame:
        """Builds ordered feature DataFrame for batch raw transactions."""
        if isinstance(raw_tx_inputs, pd.DataFrame):
            records = raw_tx_inputs.to_dict(orient="records")
            raw_txs = [RawTransaction.from_dict(r) for r in records]
        elif isinstance(raw_tx_inputs, list):
            raw_txs = [RawTransaction.from_dict(r) if isinstance(r, dict) else r for r in raw_tx_inputs]
        else:
            raise FeatureValidationError("Unsupported raw transactions input format for batch feature engineering.")

        contexts = self.context_service.get_context_batch(raw_txs)

        feature_dicts = []
        for tx, ctx in zip(raw_txs, contexts):
            f_dict: Dict[str, Any] = {}
            for builder in self.registry.get_builders():
                f_dict.update(builder.build(tx, ctx))
            feature_dicts.append(f_dict)

        return self._assemble_and_align_dataframe(feature_dicts)

    def _assemble_and_align_dataframe(self, feature_dicts: List[Dict[str, Any]]) -> pd.DataFrame:
        """Aligns generated feature dictionaries against model feature_order."""
        df = pd.DataFrame(feature_dicts)

        # Fill missing features with 0.0
        missing = [col for col in self.feature_order if col not in df.columns]
        for col in missing:
            df[col] = 0.0

        # Fill NaNs with 0.0
        df = df.fillna(0.0)

        # Strict feature ordering
        aligned_df = df[self.feature_order].copy()
        return aligned_df
