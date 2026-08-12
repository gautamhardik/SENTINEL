"""
Unit tests for ML Experiment training configuration.
"""
from fraud_detection.config import AppConfig


def test_app_config_defaults():
    config = AppConfig()
    assert config.target_column == "is_laundering"
    assert config.timestamp_column == "Timestamp"
