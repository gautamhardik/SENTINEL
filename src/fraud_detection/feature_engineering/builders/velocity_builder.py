"""
VelocityBuilder calculating time delta and transaction speed features.
"""
from datetime import datetime
from typing import Any, Dict

import pandas as pd

from fraud_detection.core.contracts import HistoricalContext, RawTransaction
from fraud_detection.feature_engineering.builders.base_builder import BaseFeatureBuilder


class VelocityBuilder(BaseFeatureBuilder):
    """Computes time delta velocity features relative to previous transactions."""

    def build(self, transaction: RawTransaction, context: HistoricalContext) -> Dict[str, Any]:
        try:
            current_dt = datetime.fromisoformat(str(transaction.Timestamp).replace(" ", "T"))
        except Exception:
            current_dt = datetime.now()

        # Sender time delta
        sender_hist = context.sender_history
        if not sender_hist.empty and "Timestamp" in sender_hist.columns:
            ts_series = pd.to_datetime(sender_hist["Timestamp"], errors="coerce").dropna()
            prior_ts = ts_series[ts_series < current_dt]
            if not prior_ts.empty:
                last_ts = prior_ts.max()
                delta_sec = max(0.0, (current_dt - last_ts).total_seconds())
            else:
                delta_sec = 999999.0
        else:
            delta_sec = 999999.0

        # Receiver time delta
        receiver_hist = context.receiver_history
        if not receiver_hist.empty and "Timestamp" in receiver_hist.columns:
            r_ts_series = pd.to_datetime(receiver_hist["Timestamp"], errors="coerce").dropna()
            r_prior_ts = r_ts_series[r_ts_series < current_dt]
            if not r_prior_ts.empty:
                r_last_ts = r_prior_ts.max()
                r_delta_sec = max(0.0, (current_dt - r_last_ts).total_seconds())
            else:
                r_delta_sec = 999999.0
        else:
            r_delta_sec = 999999.0

        rapid_transfer_flag = 1.0 if delta_sec <= 300.0 else 0.0
        receiver_rapid_flag = 1.0 if r_delta_sec <= 300.0 else 0.0
        days_since_last = delta_sec / 86400.0

        return {
            "numeric__seconds_since_last_tx": float(delta_sec),
            "numeric__receiver_seconds_since_last_tx": float(r_delta_sec),
            "numeric__rapid_transfer_flag": float(rapid_transfer_flag),
            "numeric__days_since_last_transaction": float(days_since_last),
            "numeric__receiver_rapid_flag": float(receiver_rapid_flag),
        }
