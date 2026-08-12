"""
Unit tests for CalibrationEngine, ProductionPreprocessor, PredictionService, DataIO, and Utilities.
"""
import numpy as np

from fraud_detection.calibration import CalibrationEngine
from fraud_detection.logging import StructuredLogger
from fraud_detection.telemetry import LatencyProfiler
from fraud_detection.utils import Timer, generate_request_id, hash_payload


def test_utils():
    req_id = generate_request_id()
    assert req_id.startswith("req_")

    h = hash_payload("test_payload")
    assert len(h) == 16

    with Timer() as t:
        _ = 1 + 1
    assert t.duration_ms >= 0


def test_telemetry():
    profiler = LatencyProfiler()
    profiler.start_stage("test_stage")
    dur = profiler.end_stage("test_stage")
    assert dur >= 0
    assert "test_stage" in profiler.stage_latencies
    assert profiler.total_latency_ms >= 0


def test_calibration_engine():
    class DummyCalibrator:
        def predict_proba(self, X):
            return np.array([[0.8, 0.2], [0.1, 0.9]])

    engine = CalibrationEngine(calibrator_binary=DummyCalibrator())
    probs = engine.calibrate(np.array([0.2, 0.9]))
    assert len(probs) == 2
    assert probs[1] == 0.9


def test_structured_logger(caplog):
    logger = StructuredLogger(name="TestLogger", mask_sensitive=True)
    logger.info("Test message", {"ssn": "123-45-6789", "amount": 500})
    assert "MASKED" in caplog.text
