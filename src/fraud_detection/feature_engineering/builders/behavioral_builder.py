"""
BehavioralBuilder calculating account history sums, means, ratios, network degrees, and statistical variance features.
"""
import math
from typing import Any, Dict

import numpy as np

from fraud_detection.core.contracts import HistoricalContext, RawTransaction
from fraud_detection.feature_engineering.builders.base_builder import BaseFeatureBuilder


class BehavioralBuilder(BaseFeatureBuilder):
    """Computes transaction, behavioral, network degree, and statistical variance features."""

    def build(self, transaction: RawTransaction, context: HistoricalContext) -> Dict[str, Any]:
        amount_paid = float(transaction.Amount_Paid)
        amount_received = float(transaction.Amount_Received)
        is_amount_outlier = float(transaction.is_amount_outlier)

        amount_diff = amount_paid - amount_received
        amount_ratio = amount_paid / (amount_received + 1e-5)
        log_amount = math.log1p(max(0.0, amount_paid))

        self_transfer = 1.0 if str(transaction.From_Account) == str(transaction.To_Account) else 0.0
        cross_bank = 1.0 if str(transaction.From_Bank) != str(transaction.To_Bank) else 0.0
        high_value = 1.0 if amount_paid >= 10000.0 else 0.0
        zero_amount = 1.0 if amount_paid == 0.0 else 0.0
        curr_mismatch = 1.0 if str(transaction.Payment_Currency) != str(transaction.Receiving_Currency) else 0.0

        sender_hist = context.sender_history
        receiver_hist = context.receiver_history

        # Sender history statistics
        if not sender_hist.empty and "Amount_Paid" in sender_hist.columns:
            amounts = sender_hist["Amount_Paid"].astype(float).values
            tx_count = len(amounts)
            total_paid = float(np.sum(amounts))
            avg_amount = float(np.mean(amounts))
            max_amount = float(np.max(amounts))
            min_amount = float(np.min(amounts))
            variance = float(np.var(amounts)) if tx_count > 1 else 0.0
            std_dev = float(np.sqrt(variance))

            if "To_Account" in sender_hist.columns:
                unique_counterparties = len(set(sender_hist["To_Account"].dropna().astype(str)))
            else:
                unique_counterparties = 0
            sender_out_degree = tx_count
        else:
            tx_count = 0
            total_paid = 0.0
            avg_amount = amount_paid
            max_amount = amount_paid
            min_amount = amount_paid
            variance = 0.0
            std_dev = 0.0
            unique_counterparties = 0
            sender_out_degree = 0

        # Receiver history statistics
        if not receiver_hist.empty and ("Amount_Received" in receiver_hist.columns or "Amount_Paid" in receiver_hist.columns):
            r_col = "Amount_Received" if "Amount_Received" in receiver_hist.columns else "Amount_Paid"
            r_amounts = receiver_hist[r_col].astype(float).values
            total_received = float(np.sum(r_amounts))
            receiver_in_degree = len(r_amounts)
        else:
            total_received = 0.0
            receiver_in_degree = 0

        ratio_to_avg = amount_paid / (avg_amount + 1e-5)
        ratio_to_max = amount_paid / (max_amount + 1e-5)
        net_flow = total_paid - total_received

        z_score = (amount_paid - avg_amount) / (std_dev + 1e-5) if std_dev > 1e-5 else 0.0
        coeff_var = std_dev / (avg_amount + 1e-5)

        return {
            "numeric__Amount_Paid": amount_paid,
            "numeric__Amount_Received": amount_received,
            "numeric__is_amount_outlier": is_amount_outlier,
            "numeric__amount_paid": amount_paid,
            "numeric__amount_received": amount_received,
            "numeric__amount_difference": amount_diff,
            "numeric__amount_ratio": amount_ratio,
            "numeric__log_amount": log_amount,
            "numeric__self_transfer_flag": self_transfer,
            "numeric__cross_bank_flag": cross_bank,
            "numeric__high_value_flag": high_value,
            "numeric__zero_amount_flag": zero_amount,
            "numeric__currency_mismatch_flag": curr_mismatch,
            "numeric__account_transaction_count": float(tx_count),
            "numeric__account_total_paid": total_paid,
            "numeric__account_total_received": total_received,
            "numeric__account_avg_amount": avg_amount,
            "numeric__account_max_amount": max_amount,
            "numeric__account_min_amount": min_amount,
            "numeric__ratio_to_account_average": ratio_to_avg,
            "numeric__ratio_to_account_max": ratio_to_max,
            "numeric__account_net_flow": net_flow,
            "numeric__amount_zscore": z_score,
            "numeric__account_variance": variance,
            "numeric__account_std": std_dev,
            "numeric__coefficient_of_variation": coeff_var,
            "numeric__sender_out_degree": float(sender_out_degree),
            "numeric__receiver_in_degree": float(receiver_in_degree),
            "numeric__unique_counterparties": float(unique_counterparties),
        }
