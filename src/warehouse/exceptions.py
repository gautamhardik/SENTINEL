"""
Custom Warehouse Exception Hierarchy.
"""

class WarehouseError(Exception):
    """Base exception for all warehouse operations."""
    pass

class SchemaError(WarehouseError):
    """Raised when schema creation or DDL fails."""
    pass

class ValidationError(WarehouseError):
    """Raised when integrity validation gates fail."""
    pass

class ConnectionError(WarehouseError):
    """Raised when database connection fails."""
    pass

class ETLError(WarehouseError):
    """Raised when ETL data loading encounters unrecoverable errors."""
    pass
