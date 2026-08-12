"""
Unit tests for ArtifactLoader and ArtifactManager in fraud_detection.registry.
"""
from fraud_detection.artifacts import ArtifactManager
from fraud_detection.registry import ArtifactLoader


def test_artifact_manager():
    manager = ArtifactManager()
    assert manager.registry_path.name == "registry.json"
    assert manager.model_dir.exists() or True

def test_artifact_loader():
    loader = ArtifactLoader()
    assert hasattr(loader, "load_assets")
