"""
Unit tests for ML Metrics calculation and Brier score calibration loss.
"""
import numpy as np
from sklearn.metrics import auc, brier_score_loss, precision_recall_curve, roc_auc_score


def test_metrics_calculation():
    y_true = np.array([0, 0, 1, 1, 0, 1])
    y_prob = np.array([0.1, 0.2, 0.9, 0.4, 0.1, 0.8])

    roc_auc = roc_auc_score(y_true, y_prob)
    prec, rec, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = auc(rec, prec)
    brier = brier_score_loss(y_true, y_prob)

    assert roc_auc > 0.5
    assert pr_auc > 0.0
    assert 0.0 <= brier <= 1.0
