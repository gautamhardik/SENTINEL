"""
HistoryWriter persisting newly processed transactions back into the HistoryRepository.
"""
from typing import Any, Dict, Union

import pandas as pd

from fraud_detection.core.contracts import RawTransaction
from fraud_detection.history.repository import HistoryRepository


class HistoryWriter:
    """Persists newly scored transactions into the history store for real-time future inference context."""

    def __init__(self, repository: HistoryRepository):
        self.repository = repository

    def persist_transaction(self, transaction: Union[RawTransaction, Dict[str, Any], pd.DataFrame]) -> None:
        """Persists a single or batch transaction into the history repository."""
        if isinstance(transaction, RawTransaction):
            df_new = pd.DataFrame([{
                "transaction_key": transaction.transaction_id,
                "Timestamp": transaction.Timestamp,
                "From_Account": transaction.From_Account,
                "To_Account": transaction.To_Account,
                "From_Bank": transaction.From_Bank,
                "To_Bank": transaction.To_Bank,
                "Amount_Paid": transaction.Amount_Paid,
                "Amount_Received": transaction.Amount_Received,
                "Payment_Format": transaction.Payment_Format,
                "Payment_Currency": transaction.Payment_Currency,
                "Receiving_Currency": transaction.Receiving_Currency,
                "is_laundering": 0
            }])
        elif isinstance(transaction, dict):
            raw = RawTransaction.from_dict(transaction)
            self.persist_transaction(raw)
            return
        elif isinstance(transaction, pd.DataFrame):
            df_new = transaction.copy()
        else:
            return

        self.repository.add_transactions(df_new)
