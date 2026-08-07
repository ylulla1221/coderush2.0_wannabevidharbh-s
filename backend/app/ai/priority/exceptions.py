"""
Custom exceptions for CivicFlow AI Priority Engine.
"""

from __future__ import annotations


class PriorityEngineError(Exception):
    """Base exception for all Priority Engine failures."""
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class ValidationError(PriorityEngineError):
    """Raised when input validation fails."""
    def __init__(self, message: str) -> None:
        super().__init__(f"Validation failure: {message}")


class ConfigurationError(PriorityEngineError):
    """Raised when configuration is invalid."""
    def __init__(self, message: str) -> None:
        super().__init__(f"Configuration error: {message}")
