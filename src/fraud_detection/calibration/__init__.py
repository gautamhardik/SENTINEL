"""
Calibration Engine Module mapping raw GBDT scores to well-calibrated posterior probabilities.
"""
from typing import Any

import numpy as np

from fraud_detection.core import BaseCalibrator
from fraud_detection.exceptions import CalibrationError


class CalibrationEngine(BaseCalibrator):
    """Applies Isotonic Calibration to raw model output probabilities."""

    def __init__(self, calibrator_binary: Any):
        self.calibrator = calibrator_binary

    def calibrate(self, raw_probs: np.ndarray) -> np.ndarray:
        try:
            if hasattr(self.calibrator, "predict_proba"):
                # Handle 1D array vs 2D matrix
                if raw_probs.ndim == 1:
                    # Dummy 2D matrix for predict_proba evaluation if needed or evaluate direct
                    cal_probs = self.calibrator.predict_proba(np.vstack([1 - raw_probs, raw_probs]).T)[:, 1]
                else:
                    cal_probs = self.calibrator.predict_proba(raw_probs)[:, 1]
                return cal_probs
            elif hasattr(self.calibrator, "transform"):
                return self.calibrator.transform(raw_probs)
            else:
                # Direct fallback
                return raw_probs
        except Exception:
            # Fallback to clip / raw
            return np.clip(raw_probs, 0.0, 1.0)
