"""
Feature Service package exposing OnlineFeatureService.
"""
from fraud_detection.feature_service.feature_cache import FeatureCache, feature_cache
from fraud_detection.feature_service.online_feature_service import OnlineFeatureService

__all__ = ["OnlineFeatureService", "FeatureCache", "feature_cache"]
