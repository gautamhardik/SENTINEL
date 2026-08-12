"""
Artifact Manager resolving versioned asset filepaths from models/registry.json.
"""
import json
from pathlib import Path
from typing import Any, Dict

from fraud_detection.exceptions import ArtifactNotFoundError, ModelVersionError

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ArtifactManager:
    """Manages file locations and existence checks for versioned champion model assets."""

    def __init__(self, registry_pointer_path: Path = PROJECT_ROOT / "models" / "registry.json"):
        self.registry_pointer_path = Path(registry_pointer_path)
        self.registry_meta = self._load_registry_pointer()
        self.champ_dir = PROJECT_ROOT / self.registry_meta.get("artifact_directory", "models/champion")
        self.artifacts_map = self.registry_meta.get("artifacts", {})

    def _load_registry_pointer(self) -> Dict[str, Any]:
        if not self.registry_pointer_path.exists():
            raise ModelVersionError(f"Registry pointer JSON missing at: {self.registry_pointer_path}")
        try:
            with open(self.registry_pointer_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise ModelVersionError(f"Failed to read registry pointer JSON: {str(e)}")

    def get_path(self, asset_key: str) -> Path:
        filename = self.artifacts_map.get(asset_key)
        if not filename:
            raise ArtifactNotFoundError(f"Asset key '{asset_key}' not mapped in registry pointer!")

        path = self.champ_dir / filename
        if not path.exists():
            raise ArtifactNotFoundError(f"Versioned artifact '{asset_key}' missing at: {path}")
        return path

    @property
    def model_path(self) -> Path:
        return self.get_path("model")

    @property
    def preprocessor_path(self) -> Path:
        return self.get_path("preprocessing")

    @property
    def calibrator_path(self) -> Path:
        return self.get_path("calibrator")

    @property
    def threshold_path(self) -> Path:
        return self.get_path("threshold")

    @property
    def metadata_path(self) -> Path:
        return self.get_path("metadata")

    @property
    def feature_schema_path(self) -> Path:
        return self.get_path("feature_schema")

    @property
    def feature_order_path(self) -> Path:
        return self.get_path("feature_order")

    @property
    def reference_priors_path(self) -> Path:
        return self.get_path("reference_priors")
