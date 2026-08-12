"""
Feature Store providing in-memory TTL caching over account statistics and history lookups.
"""
import time
from typing import Any, Dict, Optional


class FeatureStore:
    """In-memory feature store with TTL caching for account profile features."""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_account_profile(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves account profile dictionary if present and not expired."""
        entry = self._cache.get(account_id)
        if not entry:
            return None
        if time.time() - entry["timestamp"] > self.ttl_seconds:
            del self._cache[account_id]
            return None
        return entry["data"]

    def put_account_profile(self, account_id: str, profile_data: Dict[str, Any]) -> None:
        """Caches account profile dictionary with current timestamp."""
        self._cache[account_id] = {
            "timestamp": time.time(),
            "data": profile_data
        }

    def clear(self) -> None:
        """Clears cache entries."""
        self._cache.clear()
