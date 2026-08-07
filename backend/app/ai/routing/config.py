"""
Runtime configuration for the CivicFlow AI Routing Engine.

All values are sourced from environment variables with safe production
defaults. No other file in this module should call os.environ directly —
everything flows through here.

Domain-knowledge lookup tables (category → department, etc.) live in
constants.py. This file holds ONLY operational thresholds and fallback
strings that an operator may legitimately need to tune without modifying
business logic.

Environment Variables
---------------------
ROUTING_DEFAULT_DEPARTMENT      Fallback department when category is unknown.
ROUTING_DEFAULT_TEAM            Fallback team when category is unknown.
ROUTING_DEFAULT_ZONE            Fallback zone when category is unknown.
ROUTING_DEFAULT_SLA_HOURS       Fallback SLA (hours) when category is unknown.
ROUTING_CRITICAL_PRIORITY_SLA   SLA override (hours) for Critical priority.
ROUTING_HIGH_PRIORITY_SLA       SLA override (hours) for High priority.
ROUTING_MEDIUM_PRIORITY_SLA     SLA override (hours) for Medium priority.
ROUTING_LOW_PRIORITY_SLA        SLA override (hours) for Low priority.
ROUTING_MIN_SLA_HOURS           Hard minimum SLA — no complaint resolves in
                                less than this many hours.
ROUTING_MAX_SLA_HOURS           Hard ceiling on SLA hours.
ROUTING_ESCALATION_SCORE_THRESHOLD
                                Priority score at or above which escalation
                                is triggered regardless of level string.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Load environment
# -----------------------------------------------------------------------------

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# -----------------------------------------------------------------------------
# Fallback values (used when a category has no entry in constants.py)
# -----------------------------------------------------------------------------

DEFAULT_DEPARTMENT: str = os.getenv(
    "ROUTING_DEFAULT_DEPARTMENT",
    "General Administration",
)

DEFAULT_TEAM: str = os.getenv(
    "ROUTING_DEFAULT_TEAM",
    "General Field Team",
)

DEFAULT_ZONE: str = os.getenv(
    "ROUTING_DEFAULT_ZONE",
    "Zone G",
)

DEFAULT_SLA_HOURS: int = int(
    os.getenv("ROUTING_DEFAULT_SLA_HOURS", "72"),
)

# -----------------------------------------------------------------------------
# Priority-level SLA overrides (hours)
#
# When a complaint's resolved priority_level is at or above a threshold,
# its SLA is reduced to this value — overriding the base category SLA
# if and only if the override is *stricter* (fewer hours).
# -----------------------------------------------------------------------------

CRITICAL_PRIORITY_SLA: int = int(
    os.getenv("ROUTING_CRITICAL_PRIORITY_SLA", "4"),
)

HIGH_PRIORITY_SLA: int = int(
    os.getenv("ROUTING_HIGH_PRIORITY_SLA", "12"),
)

MEDIUM_PRIORITY_SLA: int = int(
    os.getenv("ROUTING_MEDIUM_PRIORITY_SLA", "24"),
)

LOW_PRIORITY_SLA: int = int(
    os.getenv("ROUTING_LOW_PRIORITY_SLA", "72"),
)

# -----------------------------------------------------------------------------
# SLA hard limits
# -----------------------------------------------------------------------------

MIN_SLA_HOURS: int = int(
    os.getenv("ROUTING_MIN_SLA_HOURS", "2"),
)

MAX_SLA_HOURS: int = int(
    os.getenv("ROUTING_MAX_SLA_HOURS", "168"),  # 7 days
)

# -----------------------------------------------------------------------------
# Escalation threshold
#
# A complaint with priority_score >= this value is always escalated,
# even if its priority_level string is not in ESCALATION_PRIORITY_LEVELS.
# This provides a numeric safety net for borderline cases.
# -----------------------------------------------------------------------------

ESCALATION_SCORE_THRESHOLD: float = float(
    os.getenv("ROUTING_ESCALATION_SCORE_THRESHOLD", "70.0"),
)
