"""
ContextService unifying HistoryRepository queries and champion reference priors into a focused HistoricalContext container.
"""
from typing import Any, Dict, List, Optional

import pandas as pd

from fraud_detection.core.contracts import HistoricalContext, RawTransaction
from fraud_detection.history.repository import HistoryRepository


class ContextService:
    """Orchestrates historical transaction retrieval and champion reference priors assembly."""

    def __init__(
        self,
        repository: HistoryRepository,
        reference_priors: Optional[Dict[str, Any]] = None
    ):
        self.repository = repository
        self.reference_priors = reference_priors or {}

    def get_context_for_transaction(self, raw_tx: RawTransaction) -> HistoricalContext:
        """Fetches historical context for a single raw transaction."""
        sender_id = str(raw_tx.From_Account)
        receiver_id = str(raw_tx.To_Account)

        sender_hist = self.repository.get_account_history([sender_id])
        receiver_hist = self.repository.get_receiver_history([receiver_id])

        # Filter out current transaction if it happens to be in DB already to prevent leakage
        if not sender_hist.empty and "transaction_key" in sender_hist.columns:
            sender_hist = sender_hist[sender_hist["transaction_key"].astype(str) != str(raw_tx.transaction_id)]
        if not receiver_hist.empty and "transaction_key" in receiver_hist.columns:
            receiver_hist = receiver_hist[receiver_hist["transaction_key"].astype(str) != str(raw_tx.transaction_id)]

        is_cold_sender = sender_hist.empty
        is_cold_receiver = receiver_hist.empty

        return HistoricalContext(
            sender_history=sender_hist,
            receiver_history=receiver_hist,
            reference_priors=self.reference_priors,
            is_cold_start_sender=is_cold_sender,
            is_cold_start_receiver=is_cold_receiver
        )

    def get_context_batch(self, raw_transactions: List[RawTransaction]) -> List[HistoricalContext]:
        """Fetches context for batch transactions using unique account deduplication for maximum query efficiency."""
        unique_senders = list(set(str(tx.From_Account) for tx in raw_transactions))
        unique_receivers = list(set(str(tx.To_Account) for tx in raw_transactions))

        all_sender_hist = self.repository.get_account_history(unique_senders)
        all_receiver_hist = self.repository.get_receiver_history(unique_receivers)

        contexts = []
        for tx in raw_transactions:
            sender_id = str(tx.From_Account)
            receiver_id = str(tx.To_Account)

            if not all_sender_hist.empty:
                s_hist = all_sender_hist[all_sender_hist["From_Account"].astype(str) == sender_id]
                if "transaction_key" in s_hist.columns:
                    s_hist = s_hist[s_hist["transaction_key"].astype(str) != str(tx.transaction_id)]
            else:
                s_hist = pd.DataFrame()

            if not all_receiver_hist.empty:
                r_hist = all_receiver_hist[all_receiver_hist["To_Account"].astype(str) == receiver_id]
                if "transaction_key" in r_hist.columns:
                    r_hist = r_hist[r_hist["transaction_key"].astype(str) != str(tx.transaction_id)]
            else:
                r_hist = pd.DataFrame()

            contexts.append(HistoricalContext(
                sender_history=s_hist,
                receiver_history=r_hist,
                reference_priors=self.reference_priors,
                is_cold_start_sender=s_hist.empty,
                is_cold_start_receiver=r_hist.empty
            ))

        return contexts
