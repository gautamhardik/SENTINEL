"""
Structured JSON Logger with Field Masking support.
"""
import json
import logging
import time
from typing import Any, Dict, List


class StructuredLogger:
    """Configures structured JSON logging with sensitive data masking."""

    def __init__(self, name: str = "FraudBackend", level: str = "INFO", mask_sensitive: bool = True, sensitive_keys: List[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self.mask_sensitive = mask_sensitive
        self.sensitive_keys = sensitive_keys or ["card_number", "ssn", "cvv"]

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)

    def _mask_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        if not self.mask_sensitive or not isinstance(d, dict):
            return d
        masked = {}
        for k, v in d.items():
            if any(s_key in k.lower() for s_key in self.sensitive_keys):
                masked[k] = "***MASKED***"
            elif isinstance(v, dict):
                masked[k] = self._mask_dict(v)
            else:
                masked[k] = v
        return masked

    def info(self, msg: str, extra: Dict[str, Any] = None) -> None:
        payload = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "level": "INFO", "message": msg}
        if extra:
            payload["context"] = self._mask_dict(extra)
        self.logger.info(json.dumps(payload))

    def warning(self, msg: str, extra: Dict[str, Any] = None) -> None:
        payload = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "level": "WARNING", "message": msg}
        if extra:
            payload["context"] = self._mask_dict(extra)
        self.logger.warning(json.dumps(payload))

    def error(self, msg: str, extra: Dict[str, Any] = None) -> None:
        payload = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "level": "ERROR", "message": msg}
        if extra:
            payload["context"] = self._mask_dict(extra)
        self.logger.error(json.dumps(payload))
