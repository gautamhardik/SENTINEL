"""
RiskBuilder calculating bank fraud rates, currency risk, payment format risk, and frequency encodings from reference priors.
"""
from typing import Any, Dict

from fraud_detection.core.contracts import HistoricalContext, RawTransaction
from fraud_detection.feature_engineering.builders.base_builder import BaseFeatureBuilder


class RiskBuilder(BaseFeatureBuilder):
    """Computes risk priors and target encoded features using champion reference priors."""

    def build(self, transaction: RawTransaction, context: HistoricalContext) -> Dict[str, Any]:
        priors = context.reference_priors or {}
        bank_map = priors.get("bank_fraud_rate", {})
        format_map = priors.get("payment_format_risk", {})
        currency_map = priors.get("currency_risk", {})
        freq_map = priors.get("payment_format_freq", {})
        global_priors = priors.get("global_priors", {})

        default_fraud_rate = float(global_priors.get("fraud_rate", 0.015))

        bank_id = str(transaction.From_Bank)
        format_str = str(transaction.Payment_Format)
        currency_str = str(transaction.Payment_Currency)

        bank_fraud_rate = float(bank_map.get(bank_id, bank_map.get("default", default_fraud_rate)))
        payment_format_risk = float(format_map.get(format_str, format_map.get("default", default_fraud_rate)))
        currency_risk = float(currency_map.get(currency_str, currency_map.get("default", default_fraud_rate)))
        payment_format_encoded = float(freq_map.get(format_str, freq_map.get("default", 100)))

        return {
            "numeric__bank_fraud_rate": bank_fraud_rate,
            "numeric__payment_format_risk": payment_format_risk,
            "numeric__currency_risk": currency_risk,
            "numeric__payment_format_encoded": payment_format_encoded,
        }
