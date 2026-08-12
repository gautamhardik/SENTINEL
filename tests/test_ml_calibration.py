"""
Unit tests for CalibrationEngine in src.fraud_detection.calibration.
"""
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression

from fraud_detection.calibration import CalibrationEngine


def test_calibration_engine():
    np.random.seed(42)
    X_train = np.random.randn(50, 4)
    y_train = (X_train[:, 0] > 0).astype(int)

    X_val = np.random.randn(30, 4)
    y_val = (X_val[:, 0] > 0).astype(int)

    model = LogisticRegression()
    model.fit(X_train, y_train)

    calibrator = CalibratedClassifierCV(estimator=model, cv="prefit", method="isotonic")
    calibrator.fit(X_val, y_val)

    engine = CalibrationEngine(calibrator_binary=calibrator)
    raw_probs = model.predict_proba(X_val)[:, 1]
    cal_probs = engine.calibrate(raw_probs)

    assert len(cal_probs) == len(raw_probs)
    assert np.all(cal_probs >= 0.0) and np.all(cal_probs <= 1.0)
