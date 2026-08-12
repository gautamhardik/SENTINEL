"""
Configuration Loader Module reading app.yaml and models/registry.json into typed objects.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from fraud_detection.exceptions import ConfigurationError

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class AppConfig:
    """Central Configuration Manager for fraud_detection package."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path if config_path else PROJECT_ROOT / "configs" / "app.yaml"
        self.raw_config = self._load_yaml(self.config_path)

        app_sec = self.raw_config.get("app", {})
        model_sec = self.raw_config.get("model", {})
        logging_sec = self.raw_config.get("logging", {})
        feat_sec = self.raw_config.get("feature", {})

        self.app_name: str = app_sec.get("name", "Enterprise Fraud Detection")
        self.environment: str = app_sec.get("environment", "production")
        self.request_timeout: float = app_sec.get("request_timeout_seconds", 5.0)

        self.registry_pointer_path: Path = PROJECT_ROOT / model_sec.get("active_registry_pointer", "models/registry.json")
        self.fallback_threshold: float = model_sec.get("fallback_threshold", 0.26)
        self.max_batch_size: int = model_sec.get("max_batch_size", 10000)

        self.log_level: str = logging_sec.get("level", "INFO")
        self.mask_sensitive: bool = logging_sec.get("mask_sensitive_fields", True)
        self.sensitive_keys: List[str] = logging_sec.get("sensitive_keys", ["card_number", "ssn", "cvv"])

        self.target_column: str = feat_sec.get("target_column", "is_laundering")
        self.timestamp_column: str = feat_sec.get("timestamp_column", "Timestamp")
        self.id_columns: List[str] = feat_sec.get("id_columns", ["Account_ID", "Transaction_ID"])

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(f"Failed to parse configuration YAML at {path}: {str(e)}")
