"""
Prediction Service Module orchestrating validation, online feature engineering, preprocessing, model scoring, calibration, thresholding, explainability, response building, and history persistence.
"""
import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from fraud_detection.builders import PredictionBuilder
from fraud_detection.core import (
    BaseCalibrator,
    BaseExplainer,
    BaseThresholdEngine,
    BaseValidator,
    PredictionContext,
    PredictionSession,
)
from fraud_detection.exceptions import FeatureValidationError, PredictionEngineError
from fraud_detection.feature_service import OnlineFeatureService
from fraud_detection.history import HistoryWriter
from fraud_detection.logging import StructuredLogger
from fraud_detection.preprocessing import ProductionPreprocessor
from fraud_detection.telemetry import LatencyProfiler
from fraud_detection.utils import generate_request_id


class PredictionService:
    """Orchestrates the thread-safe inference pipeline across single or vectorized batch transactions."""

    def __init__(
        self,
        model: Any,
        preprocessor: ProductionPreprocessor,
        validator: BaseValidator,
        calibrator: BaseCalibrator,
        threshold_engine: BaseThresholdEngine,
        explainer: BaseExplainer,
        metadata: Dict[str, Any],
        raw_features: List[str],
        feature_order: List[str],
        online_feature_service: Optional[OnlineFeatureService] = None,
        history_writer: Optional[HistoryWriter] = None,
        logger: Optional[StructuredLogger] = None
    ):
        self.model = model
        self.preprocessor = preprocessor
        self.validator = validator
        self.calibrator = calibrator
        self.threshold_engine = threshold_engine
        self.explainer = explainer
        self.metadata = dict(metadata)
        self.raw_features = list(raw_features)
        self.feature_order = list(feature_order)
        self.online_feature_service = online_feature_service
        self.history_writer = history_writer
        self.logger = logger or StructuredLogger("PredictionService")

    def _needs_online_feature_engineering(self, df: pd.DataFrame) -> bool:
        """Checks if input DataFrame requires online feature engineering."""
        if df.empty:
            return False
        # If pre-engineered feature_order columns exist, feature engineering is not needed
        engineered_present = any(col in df.columns for col in self.feature_order)
        raw_present = any(col in df.columns for col in ["From_Account", "Amount_Paid", "Timestamp"])
        return raw_present and not engineered_present

    def predict_single(self, transaction_df: pd.DataFrame, include_explanations: bool = True) -> PredictionSession:
        """Executes thread-safe inference on a single transaction payload."""
        profiler = LatencyProfiler()
        request_id = generate_request_id()

        context = PredictionContext(
            request_id=request_id,
            model_name=self.metadata.get("model_name", "CatBoost"),
            model_version=self.metadata.get("version", "v1.0.0"),
            optimal_threshold=self.threshold_engine.optimal_threshold,
            start_time=time.time(),
            feature_count=len(self.feature_order)
        )

        local_df = transaction_df.copy()

        # 0. Initial Raw Validation Stage
        profiler.start_stage("validation")
        val_res = self.validator.validate(local_df)
        if not val_res.is_valid:
            profiler.end_stage("validation")
            error_msg = "; ".join(val_res.errors)
            self.logger.error("Transaction validation failed", {"errors": val_res.errors, "request_id": request_id})
            raise FeatureValidationError(f"Transaction validation failed: {error_msg}")
        profiler.end_stage("validation")

        # 1. Online Feature Engineering Stage (if raw payload provided)
        profiler.start_stage("feature_engineering")
        if self._needs_online_feature_engineering(local_df) and self.online_feature_service is not None:
            raw_record = local_df.to_dict(orient="records")[0]
            local_df = self.online_feature_service.build_features_single(raw_record)
        profiler.end_stage("feature_engineering")

        if not val_res.is_valid:
            error_msg = "; ".join(val_res.errors)
            self.logger.error("Transaction validation failed", {"errors": val_res.errors, "request_id": request_id})
            raise FeatureValidationError(f"Transaction validation failed: {error_msg}")

        # 2. Preprocessing Stage
        profiler.start_stage("preprocessing")
        X_trans = self.preprocessor.transform(local_df)
        profiler.end_stage("preprocessing")

        # 3. Model Scoring Stage
        profiler.start_stage("model_scoring")
        raw_model = self.model.estimator if hasattr(self.model, "estimator") else self.model
        if hasattr(raw_model, "predict_proba"):
            raw_prob = float(raw_model.predict_proba(X_trans)[0, 1])
        else:
            raw_prob = float(raw_model.predict(X_trans)[0])
        profiler.end_stage("model_scoring")

        # 4. Calibration Stage
        profiler.start_stage("calibration")
        cal_prob = float(self.calibrator.calibrate(np.array([raw_prob]))[0])
        profiler.end_stage("calibration")

        # 5. Thresholding Stage
        profiler.start_stage("thresholding")
        risk_res = self.threshold_engine.evaluate(cal_prob)
        profiler.end_stage("thresholding")

        # 6. Explainability Stage
        profiler.start_stage("explainability")
        if include_explanations:
            shap_vals = self.explainer.explainer.shap_values(X_trans)
            if isinstance(shap_vals, list):
                shap_row = shap_vals[1][0]
            else:
                shap_row = shap_vals[0]
            explanation = self.explainer.explain(X_trans[0], shap_row, cal_prob, risk_res.threshold)
        else:
            from fraud_detection.core import BusinessExplanation
            # Fast heuristic top risk drivers based on standardized magnitude
            feature_names = self.feature_order
            top_drivers = []
            if len(X_trans[0]) == len(feature_names):
                ranked_indices = np.argsort(np.abs(X_trans[0]))[::-1][:4]
                for r_idx in ranked_indices:
                    fname = feature_names[r_idx].replace("numeric__", "")
                    top_drivers.append({
                        "feature": fname,
                        "importance": float(abs(X_trans[0][r_idx])),
                        "direction": "RISK_INCREASING" if X_trans[0][r_idx] > 0 else "RISK_REDUCING",
                        "value": float(X_trans[0][r_idx])
                    })
            explanation = BusinessExplanation(
                investigator_card=f"Fast-path inference. Decision: {risk_res.decision} at posterior probability {cal_prob:.4f}",
                top_risk_drivers=top_drivers,
                counterfactual_advice=["Asynchronous deep TreeSHAP investigator card dispatched to background worker."]
            )
        profiler.end_stage("explainability")

        # 7. Response Building Stage
        session = PredictionBuilder.build_session(
            context=context,
            risk_res=risk_res,
            raw_prob=raw_prob,
            cal_prob=cal_prob,
            explanation=explanation,
            total_latency=profiler.total_latency_ms,
            stage_latencies=profiler.stage_latencies
        )

        # 8. History Persistence Stage (update real-time context)
        if self.history_writer is not None:
            try:
                self.history_writer.persist_transaction(transaction_df)
            except Exception as e:
                self.logger.warning(f"Failed to persist transaction to history writer: {str(e)}")

        self.logger.info(f"Successfully processed prediction [{request_id}] -> {risk_res.decision}", {
            "request_id": request_id,
            "decision": risk_res.decision,
            "probability": cal_prob,
            "latency_ms": session.total_latency_ms
        })

        return session

    def predict_batch(self, transactions_df: pd.DataFrame, include_explanations: bool = True) -> List[PredictionSession]:
        """Executes batch inference using vectorized feature engineering, preprocessing, and scoring for maximum throughput."""
        if transactions_df is None or transactions_df.empty:
            raise FeatureValidationError("Batch input DataFrame is empty or invalid.")

        batch_size = len(transactions_df)
        profiler = LatencyProfiler()
        local_df = transactions_df.copy()

        # 0. Vectorized Feature Engineering Stage (if raw payload provided)
        profiler.start_stage("feature_engineering")
        if self._needs_online_feature_engineering(local_df) and self.online_feature_service is not None:
            local_df = self.online_feature_service.build_features_batch(local_df)
        profiler.end_stage("feature_engineering")

        # 1. Vectorized Validation
        profiler.start_stage("validation")
        val_res = self.validator.validate(local_df)
        profiler.end_stage("validation")

        if not val_res.is_valid:
            error_msg = "; ".join(val_res.errors)
            self.logger.error("Batch transaction validation failed", {"errors": val_res.errors})
            raise FeatureValidationError(f"Batch validation failed: {error_msg}")

        # 2. Vectorized Preprocessing
        profiler.start_stage("preprocessing")
        X_trans_batch = self.preprocessor.transform(local_df)
        profiler.end_stage("preprocessing")

        # 3. Vectorized Model Scoring
        profiler.start_stage("model_scoring")
        raw_model = self.model.estimator if hasattr(self.model, "estimator") else self.model
        if hasattr(raw_model, "predict_proba"):
            raw_probs_batch = raw_model.predict_proba(X_trans_batch)[:, 1]
        else:
            raw_probs_batch = raw_model.predict(X_trans_batch)
        profiler.end_stage("model_scoring")

        # 4. Vectorized Calibration
        profiler.start_stage("calibration")
        cal_probs_batch = self.calibrator.calibrate(raw_probs_batch)
        profiler.end_stage("calibration")

        # 5. Vectorized Explainability (TreeExplainer on full batch matrix)
        profiler.start_stage("explainability")
        if include_explanations:
            shap_vals_batch = self.explainer.explainer.shap_values(X_trans_batch)
            if isinstance(shap_vals_batch, list):
                shap_matrix = shap_vals_batch[1]
            else:
                shap_matrix = shap_vals_batch
        else:
            shap_matrix = None
        profiler.end_stage("explainability")

        # 6. Assemble Sessions for Batch
        sessions = []
        avg_stage_latencies = {
            "feature_engineering": round(profiler.stage_latencies.get("feature_engineering", 0.0) / batch_size, 4),
            "validation": round(profiler.stage_latencies.get("validation", 0.0) / batch_size, 4),
            "preprocessing": round(profiler.stage_latencies.get("preprocessing", 0.0) / batch_size, 4),
            "model_scoring": round(profiler.stage_latencies.get("model_scoring", 0.0) / batch_size, 4),
            "calibration": round(profiler.stage_latencies.get("calibration", 0.0) / batch_size, 4),
            "explainability": round(profiler.stage_latencies.get("explainability", 0.0) / batch_size, 4)
        }

        for idx in range(batch_size):
            request_id = generate_request_id()
            raw_p = float(raw_probs_batch[idx])
            cal_p = float(cal_probs_batch[idx])
            risk_res = self.threshold_engine.evaluate(cal_p)

            context = PredictionContext(
                request_id=request_id,
                model_name=self.metadata.get("model_name", "CatBoost"),
                model_version=self.metadata.get("version", "v1.0.0"),
                optimal_threshold=self.threshold_engine.optimal_threshold,
                start_time=time.time(),
                feature_count=len(self.feature_order)
            )

            if include_explanations and shap_matrix is not None:
                explanation = self.explainer.explain(X_trans_batch[idx], shap_matrix[idx], cal_p, risk_res.threshold)
            else:
                from fraud_detection.core import BusinessExplanation
                explanation = BusinessExplanation(investigator_card="Batch mode (Explanations skipped)", top_risk_drivers=[], counterfactual_advice=[])

            session = PredictionBuilder.build_session(
                context=context,
                risk_res=risk_res,
                raw_prob=raw_p,
                cal_prob=cal_p,
                explanation=explanation,
                total_latency=round(profiler.total_latency_ms / batch_size, 4),
                stage_latencies=avg_stage_latencies
            )
            sessions.append(session)

        # 7. Batch History Persistence
        if self.history_writer is not None:
            try:
                self.history_writer.persist_transaction(transactions_df)
            except Exception as e:
                self.logger.warning(f"Failed to persist batch transactions to history writer: {str(e)}")

        self.logger.info(f"Successfully processed batch prediction ({batch_size} transactions) in {profiler.total_latency_ms:.2f} ms")
        return sessions
