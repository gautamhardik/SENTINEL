"""
Engine Factory Module creating and wiring all backend services cleanly.
"""
from typing import Optional

from fraud_detection.artifacts import ArtifactManager
from fraud_detection.calibration import CalibrationEngine
from fraud_detection.config import AppConfig
from fraud_detection.explainability import ExplainabilityEngine
from fraud_detection.feature_service import OnlineFeatureService
from fraud_detection.history import HistoryRepository, HistoryWriter
from fraud_detection.inference import PredictionEngine
from fraud_detection.logging import StructuredLogger
from fraud_detection.preprocessing import ProductionPreprocessor
from fraud_detection.registry import ArtifactLoader
from fraud_detection.retrieval import ContextService
from fraud_detection.services import PredictionService
from fraud_detection.thresholding import ThresholdEngine
from fraud_detection.validation import FeatureValidator


class EngineFactory:
    """Instantiates and wires all dependencies into a ready-to-use PredictionEngine facade."""

    @staticmethod
    def create(config: Optional[AppConfig] = None, history_repository: Optional[HistoryRepository] = None) -> PredictionEngine:
        cfg = config if config else AppConfig()
        logger = StructuredLogger(name="FraudEngine", level=cfg.log_level, mask_sensitive=cfg.mask_sensitive, sensitive_keys=cfg.sensitive_keys)

        logger.info("Initializing Enterprise Fraud Detection Engine via EngineFactory...")
        manager = ArtifactManager(registry_pointer_path=cfg.registry_pointer_path)
        loader = ArtifactLoader(manager=manager)

        assets = loader.load_assets()

        # Wire history layer & context service
        history_repo = history_repository if history_repository is not None else HistoryRepository()
        history_writer = HistoryWriter(repository=history_repo)
        context_service = ContextService(
            repository=history_repo,
            reference_priors=assets.get("reference_priors", {})
        )
        online_feature_service = OnlineFeatureService(
            context_service=context_service,
            feature_order=assets["feature_order"]
        )

        validator = FeatureValidator(
            raw_features=assets["raw_features"],
            feature_order=assets["feature_order"]
        )
        preprocessor = ProductionPreprocessor(
            preprocessor_binary=assets["preprocessor"],
            raw_features=assets["raw_features"],
            feature_order=assets["feature_order"]
        )
        calibrator = CalibrationEngine(calibrator_binary=assets["calibrator"])
        threshold_engine = ThresholdEngine(optimal_threshold=assets["optimal_threshold"])
        explainer = ExplainabilityEngine(
            raw_model=assets["model"],
            feature_order=assets["feature_order"]
        )

        service = PredictionService(
            model=assets["model"],
            preprocessor=preprocessor,
            validator=validator,
            calibrator=calibrator,
            threshold_engine=threshold_engine,
            explainer=explainer,
            metadata=assets["metadata"],
            raw_features=assets["raw_features"],
            feature_order=assets["feature_order"],
            online_feature_service=online_feature_service,
            history_writer=history_writer,
            logger=logger
        )

        engine = PredictionEngine(service=service)
        logger.info("✅ Enterprise Fraud Detection Engine initialized successfully!")
        return engine
