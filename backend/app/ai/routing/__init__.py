"""
CivicFlow AI Routing Engine.

Public interface for the routing module.  External code should import
only from here; no internal sub-module should be imported directly.

Usage::

    from app.ai.routing import calculate_route

    result = calculate_route(
        complaint_data=llm_result,
        duplicate_data=duplicate_result,
        priority_data=priority_result,
    )
"""

from __future__ import annotations

from .exceptions import RoutingConfigurationError, RoutingEngineError, RoutingValidationError
from .models import RoutingInput, RoutingResult
from .routing_engine import calculate_route

__all__ = [
    "calculate_route",
    "RoutingInput",
    "RoutingResult",
    "RoutingEngineError",
    "RoutingValidationError",
    "RoutingConfigurationError",
]
