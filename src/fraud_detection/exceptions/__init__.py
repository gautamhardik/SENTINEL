"""
Custom Exception Hierarchy for fraud_detection package.
"""

class FraudDetectionBaseException(Exception):
    """Base exception class for all fraud_detection package errors."""
    pass


class ConfigurationError(FraudDetectionBaseException):
    """Raised when configuration files or YAML parameters are invalid or missing."""
    pass


class ArtifactNotFoundError(FraudDetectionBaseException):
    """Raised when required model joblib or schema JSON artifacts are missing from registry."""
    pass


class SchemaMismatchError(FraudDetectionBaseException):
    """Raised when inference input columns do not match expected feature store schema."""
    pass


class FeatureValidationError(FraudDetectionBaseException):
    """Raised when incoming transaction payload fails data type, range, or null validation checks."""
    pass


class CalibrationError(FraudDetectionBaseException):
    """Raised when probability calibration fails."""
    pass


class PredictionEngineError(FraudDetectionBaseException):
    """Raised when scoring or inference pipeline fails."""
    pass


class ModelVersionError(FraudDetectionBaseException):
    """Raised when active registry version pointer is invalid or corrupted."""
    pass
