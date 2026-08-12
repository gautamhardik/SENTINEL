"""
Generic utilities for UUID generation, string hashing, timing, and version resolution.
"""
import hashlib
import time
import uuid
from typing import Any, Dict


def generate_request_id() -> str:
    """Generates unique UUID4 request tracing ID."""
    return f"req_{uuid.uuid4().hex[:12]}"


def hash_payload(payload_str: str) -> str:
    """Computes SHA-256 hash of payload string for caching or idempotency checks."""
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()[:16]


class Timer:
    """Context manager measuring execution duration in milliseconds."""
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = time.time()

    @property
    def duration_ms(self) -> float:
        if hasattr(self, "end"):
            return round((self.end - self.start) * 1000.0, 4)
        return round((time.time() - self.start) * 1000.0, 4)
