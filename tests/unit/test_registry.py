"""
Unit tests for ArtifactLoader and ArtifactManager.
"""
from fraud_detection.artifacts import ArtifactManager
from fraud_detection.registry import ArtifactLoader


def test_artifact_manager_paths():
    manager = ArtifactManager()
    assert manager.model_path.exists()
    assert manager.preprocessor_path.exists()
    assert manager.calibrator_path.exists()
    assert manager.threshold_path.exists()


def test_artifact_loader_assets():
    loader = ArtifactLoader()
    assets = loader.load_assets()
    assert "model" in assets
    assert "preprocessor" in assets
    assert "calibrator" in assets
    assert "optimal_threshold" in assets
    assert isinstance(assets["optimal_threshold"], float)
    assert isinstance(assets["raw_features"], list)
    assert len(assets["feature_order"]) == 61
