"""
TemporalBuilder calculating time, cyclical, and business hour features.
"""
import math
from datetime import datetime
from typing import Any, Dict

from fraud_detection.core.contracts import HistoricalContext, RawTransaction
from fraud_detection.feature_engineering.builders.base_builder import BaseFeatureBuilder


class TemporalBuilder(BaseFeatureBuilder):
    """Computes temporal and cyclical trig features from transaction timestamp."""

    def build(self, transaction: RawTransaction, context: HistoricalContext) -> Dict[str, Any]:
        ts_str = str(transaction.Timestamp)
        try:
            dt = datetime.fromisoformat(ts_str.replace(" ", "T"))
        except Exception:
            dt = datetime.now()

        hour = dt.hour
        weekday = dt.weekday() + 1  # 1 to 7 matching training (Monday=1)
        month = dt.month
        quarter = (month - 1) // 3 + 1

        weekend_flag = 1 if weekday >= 6 else 0
        business_hours_flag = 1 if (8 <= hour < 18) else 0
        night_flag = 1 if (hour < 6 or hour >= 22) else 0

        sin_hour = math.sin(2 * math.pi * hour / 24.0)
        cos_hour = math.cos(2 * math.pi * hour / 24.0)
        sin_day = math.sin(2 * math.pi * weekday / 7.0)
        cos_day = math.cos(2 * math.pi * weekday / 7.0)

        return {
            "numeric__hour": float(hour),
            "numeric__weekday": float(weekday),
            "numeric__month": float(month),
            "numeric__quarter": float(quarter),
            "numeric__weekend_flag": float(weekend_flag),
            "numeric__business_hours_flag": float(business_hours_flag),
            "numeric__night_transaction_flag": float(night_flag),
            "numeric__sin_hour": float(sin_hour),
            "numeric__cos_hour": float(cos_hour),
            "numeric__sin_day": float(sin_day),
            "numeric__cos_day": float(cos_day),
        }
