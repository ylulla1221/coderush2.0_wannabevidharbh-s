"""
Configuration for the CivicFlow AI Priority Engine.

This module contains configurable weights and thresholds used by the
deterministic priority scoring engine.

Business lookup tables (urgency mappings, category severities, etc.)
are intentionally kept in constants.py.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Load environment variables
# -----------------------------------------------------------------------------

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# -----------------------------------------------------------------------------
# Component Weights
#
# Total = 100
# -----------------------------------------------------------------------------

URGENCY_WEIGHT: float = float(
    os.getenv("PRIORITY_URGENCY_WEIGHT", "35")
)

CATEGORY_WEIGHT: float = float(
    os.getenv("PRIORITY_CATEGORY_WEIGHT", "25")
)

COMMUNITY_IMPACT_WEIGHT: float = float(
    os.getenv("PRIORITY_COMMUNITY_IMPACT_WEIGHT", "20")
)

CONFIDENCE_WEIGHT: float = float(
    os.getenv("PRIORITY_CONFIDENCE_WEIGHT", "10")
)

SLA_WEIGHT: float = float(
    os.getenv("PRIORITY_SLA_WEIGHT", "10")
)

# -----------------------------------------------------------------------------
# Priority Thresholds
# -----------------------------------------------------------------------------

CRITICAL_THRESHOLD: float = float(
    os.getenv("PRIORITY_CRITICAL_THRESHOLD", "90")
)

HIGH_THRESHOLD: float = float(
    os.getenv("PRIORITY_HIGH_THRESHOLD", "70")
)

MEDIUM_THRESHOLD: float = float(
    os.getenv("PRIORITY_MEDIUM_THRESHOLD", "40")
)

LOW_THRESHOLD: float = float(
    os.getenv("PRIORITY_LOW_THRESHOLD", "0")
)

# -----------------------------------------------------------------------------
# Confidence Thresholds
# -----------------------------------------------------------------------------

HIGH_CONFIDENCE_THRESHOLD: float = float(
    os.getenv("PRIORITY_HIGH_CONFIDENCE_THRESHOLD", "0.95")
)

MEDIUM_CONFIDENCE_THRESHOLD: float = float(
    os.getenv("PRIORITY_MEDIUM_CONFIDENCE_THRESHOLD", "0.90")
)

LOW_CONFIDENCE_THRESHOLD: float = float(
    os.getenv("PRIORITY_LOW_CONFIDENCE_THRESHOLD", "0.80")
)

# -----------------------------------------------------------------------------
# SLA Thresholds (Complaint Age in Hours)
# -----------------------------------------------------------------------------

SLA_WARNING_HOURS: int = int(
    os.getenv("PRIORITY_SLA_WARNING_HOURS", "12")
)

SLA_RISK_HOURS: int = int(
    os.getenv("PRIORITY_SLA_RISK_HOURS", "24")
)

SLA_CRITICAL_HOURS: int = int(
    os.getenv("PRIORITY_SLA_CRITICAL_HOURS", "48")
)

# -----------------------------------------------------------------------------
# Score Limits
# -----------------------------------------------------------------------------

MIN_PRIORITY_SCORE: float = 0.0
MAX_PRIORITY_SCORE: float = 100.0