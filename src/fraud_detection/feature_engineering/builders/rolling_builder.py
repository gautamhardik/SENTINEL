"""
RollingBuilder calculating lag transaction amounts and rolling window statistics (mean, std, min, max, sum, diffs).
"""
from typing import Any, Dict

import numpy as np

from fraud_detection.core.contracts import HistoricalContext, RawTransaction
from fraud_detection.feature_engineering.builders.base_builder import BaseFeatureBuilder


class RollingBuilder(BaseFeatureBuilder):
    """Computes lag features and rolling window aggregate statistics over historical account transactions."""

    def build(self, transaction: RawTransaction, context: HistoricalContext) -> Dict[str, Any]:
        amount_paid = transaction.Amount_Paid
        sender_hist = context.sender_history

        if not sender_hist.empty and "Amount_Paid" in sender_hist.columns:
            amounts = [float(v) for v in sender_hist["Amount_Paid"].values]
        else:
            amounts = []

        # Lags
        lag1 = float(amounts[-1]) if len(amounts) >= 1 else amount_paid
        lag2 = float(amounts[-2]) if len(amounts) >= 2 else amount_paid
        lag5 = float(amounts[-5]) if len(amounts) >= 5 else amount_paid

        # Rolling 5
        win5 = amounts[-5:] if amounts else [amount_paid]
        rmean5 = float(np.mean(win5))
        rstd5 = float(np.std(win5)) if len(win5) > 1 else 0.0
        rmax5 = float(np.max(win5))
        rmin5 = float(np.min(win5))
        rsum5 = float(np.sum(win5))

        # Rolling 20
        win20 = amounts[-20:] if amounts else [amount_paid]
        rmean20 = float(np.mean(win20))
        rsum20 = float(np.sum(win20))

        diff_lag1 = amount_paid - lag1
        diff_roll5 = amount_paid - rmean5

        return {
            "numeric__lag_amount_1": lag1,
            "numeric__lag_amount_2": lag2,
            "numeric__lag_amount_5": lag5,
            "numeric__rolling_mean_5": rmean5,
            "numeric__rolling_mean_20": rmean20,
            "numeric__rolling_std_5": rstd5,
            "numeric__rolling_max_5": rmax5,
            "numeric__rolling_min_5": rmin5,
            "numeric__rolling_sum_5": rsum5,
            "numeric__rolling_sum_20": rsum20,
            "numeric__amount_diff_lag1": diff_lag1,
            "numeric__amount_diff_rolling5": diff_roll5,
        }
