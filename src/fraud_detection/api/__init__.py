"""
FastAPI Serving Module for Enterprise Fraud Detection Engine.
"""
from fraud_detection.api.app import app, get_engine

__all__ = ["app", "get_engine"]
