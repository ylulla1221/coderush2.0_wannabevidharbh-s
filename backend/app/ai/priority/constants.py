"""
Constants for the CivicFlow AI Priority Engine.

This module contains business constants and lookup tables used by the
deterministic priority scoring engine.

Unlike config.py, these values represent domain knowledge rather than
runtime configuration.
"""

from typing import Final

# =============================================================================
# URGENCY LEVELS
# =============================================================================

URGENCY_CRITICAL: Final[str] = "Critical"
URGENCY_HIGH: Final[str] = "High"
URGENCY_MEDIUM: Final[str] = "Medium"
URGENCY_LOW: Final[str] = "Low"

# =============================================================================
# PRIORITY LEVELS
# =============================================================================

PRIORITY_CRITICAL: Final[str] = "Critical"
PRIORITY_HIGH: Final[str] = "High"
PRIORITY_MEDIUM: Final[str] = "Medium"
PRIORITY_LOW: Final[str] = "Low"

# =============================================================================
# SCORE LIMITS
# =============================================================================

MIN_SCORE: Final[float] = 0.0
MAX_SCORE: Final[float] = 100.0

# =============================================================================
# URGENCY SCORE LOOKUP
#
# Maximum contribution = 35
# =============================================================================

URGENCY_SCORES: Final[dict[str, float]] = {
    URGENCY_LOW: 5.0,
    URGENCY_MEDIUM: 15.0,
    URGENCY_HIGH: 25.0,
    URGENCY_CRITICAL: 35.0,
}

DEFAULT_URGENCY_SCORE: Final[float] = 15.0

# =============================================================================
# CATEGORY SEVERITY SCORES
#
# Maximum contribution = 25
# =============================================================================

CATEGORY_SCORES: Final[dict[str, float]] = {
    "Garbage": 8.0,
    "Water Leakage": 10.0,
    "Street Light": 12.0,
    "Drainage": 12.0,
    "Road Damage": 20.0,
    "Tree Fallen": 22.0,
    "Flooding": 24.0,
    "Open Manhole": 25.0,
    "Electrical Hazard": 25.0,
    "Public Safety": 25.0,
}

DEFAULT_CATEGORY_SCORE: Final[float] = 10.0

# =============================================================================
# COMMUNITY IMPACT (Duplicate Cluster Size)
#
# Maximum contribution = 20
# =============================================================================

COMMUNITY_IMPACT_SCORES: Final[dict[int, float]] = {
    1: 0.0,
    2: 5.0,
    3: 10.0,
    5: 15.0,
    10: 20.0,
}

# =============================================================================
# CONFIDENCE SCORES
#
# Maximum contribution = 10
# =============================================================================

CONFIDENCE_SCORES: Final[dict[str, float]] = {
    "HIGH": 10.0,
    "MEDIUM": 8.0,
    "LOW": 6.0,
    "VERY_LOW": 4.0,
}

# =============================================================================
# SLA RISK SCORES
#
# Complaint age (hours)
#
# Maximum contribution = 10
# =============================================================================

SLA_SCORES: Final[dict[str, float]] = {
    "SAFE": 0.0,
    "WARNING": 2.0,
    "RISK": 5.0,
    "HIGH_RISK": 8.0,
    "CRITICAL": 10.0,
}