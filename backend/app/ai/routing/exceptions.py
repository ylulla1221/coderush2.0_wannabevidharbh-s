"""
Custom exceptions for the CivicFlow AI Routing Engine.

Exception Hierarchy
-------------------
RoutingEngineError (base)
    ├── RoutingValidationError   — input schema / type failures
    └── RoutingConfigurationError — invalid or inconsistent config values

Design
------
- RoutingEngineError is the single type external callers need to catch for
  a blanket handler.
- Sub-classes give call-sites the ability to distinguish validation faults
  (bad upstream data) from configuration faults (operator misconfiguration).
- Every exception carries a ``message`` attribute so structured loggers can
  read it without having to call str(exc).
"""

from __future__ import annotations


class RoutingEngineError(Exception):
    """Base exception for all Routing Engine failures.

    Attributes:
        message: Human-readable description of the failure, suitable for
            structured logging.
    """

    def __init__(self, message: str) -> None:
        """Initialise the exception with a descriptive message.

        Args:
            message: Human-readable failure description.
        """
        self.message = message
        super().__init__(self.message)


class RoutingValidationError(RoutingEngineError):
    """Raised when the input payload fails Pydantic validation.

    Common causes:
        - Priority Engine returned a missing or wrong-typed field.
        - Duplicate Detection result omitted a required key.
        - LLM extraction produced a value outside the accepted range.

    Args:
        message: Detailed description of what field or constraint failed.
    """

    def __init__(self, message: str) -> None:
        super().__init__(f"Routing input validation failed: {message}")


class RoutingConfigurationError(RoutingEngineError):
    """Raised when config.py values are logically inconsistent.

    Common causes:
        - CRITICAL_PRIORITY_SLA > HIGH_PRIORITY_SLA (inverted SLA ladder).
        - MIN_SLA_HOURS > MAX_SLA_HOURS.
        - ESCALATION_SCORE_THRESHOLD outside [0, 100].

    Args:
        message: Detailed description of the misconfiguration.
    """

    def __init__(self, message: str) -> None:
        super().__init__(f"Routing configuration error: {message}")
