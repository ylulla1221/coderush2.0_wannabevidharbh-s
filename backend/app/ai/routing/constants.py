"""
Business lookup tables for the CivicFlow AI Routing Engine.

This module contains ONLY domain-knowledge dictionaries mapping civic complaint
categories to departments, teams, geographic zones, and SLA commitments.

Unlike config.py, the values here are not runtime-configurable — they encode
the official routing rules of the CivicFlow system. Operational thresholds
(e.g., what score triggers escalation) live in config.py.

Lookup Tables
-------------
CATEGORY_TO_DEPARTMENT      str  → str
CATEGORY_TO_TEAM            str  → str
CATEGORY_TO_ZONE            str  → str
CATEGORY_TO_BASE_SLA        str  → int  (hours)
ESCALATION_PRIORITY_LEVELS  set[str]   priority levels that trigger escalation
"""

from __future__ import annotations

from typing import Final

# =============================================================================
# DEPARTMENT MAPPINGS
#
# Each civic complaint category maps to exactly ONE responsible department.
# "Unknown" is the deterministic fallback used when a category arrives that
# does not appear in this table.
# =============================================================================

CATEGORY_TO_DEPARTMENT: Final[dict[str, str]] = {
    # Road & Infrastructure
    "Road Damage":           "Road Department",
    "Open Manhole":          "Road Department",
    "Footpath Damage":       "Road Department",
    "Road Waterlogging":     "Road Department",
    # Water & Drainage
    "Water Leakage":         "Water Supply Department",
    "No Water Supply":       "Water Supply Department",
    "Drainage Blocked":      "Water Supply Department",
    "Flooding":              "Water Supply Department",
    # Sanitation
    "Garbage":               "Sanitation Department",
    "Garbage Dump":          "Sanitation Department",
    "Dead Animal":           "Sanitation Department",
    "Open Defecation":       "Sanitation Department",
    # Electrical & Lighting
    "Street Light":          "Electricity Department",
    "Electrical Hazard":     "Electricity Department",
    "No Electricity":        "Electricity Department",
    "Broken Street Light":   "Electricity Department",
    # Public Safety & Trees
    "Tree Fallen":           "Parks Department",
    "Tree Hazard":           "Parks Department",
    "Park Maintenance":      "Parks Department",
    # Traffic
    "Traffic Signal":        "Traffic Department",
    "Illegal Parking":       "Traffic Department",
    "Broken Traffic Sign":   "Traffic Department",
    # Public Safety
    "Public Safety":         "Public Safety Department",
    "Stray Animals":         "Public Safety Department",
    "Fire Hazard":           "Public Safety Department",
    # Construction & Property
    "Illegal Construction":  "Town Planning Department",
    "Encroachment":          "Town Planning Department",
    # Noise
    "Noise Pollution":       "Environmental Department",
    "Air Pollution":         "Environmental Department",
}

DEFAULT_DEPARTMENT: Final[str] = "General Administration"

# =============================================================================
# TEAM MAPPINGS
#
# Each category maps to the specialist team within its department that
# carries out the actual field work.
# =============================================================================

CATEGORY_TO_TEAM: Final[dict[str, str]] = {
    # Road & Infrastructure
    "Road Damage":           "Road Maintenance Team",
    "Open Manhole":          "Road Safety Team",
    "Footpath Damage":       "Road Maintenance Team",
    "Road Waterlogging":     "Drainage & Road Team",
    # Water & Drainage
    "Water Leakage":         "Pipeline Repair Team",
    "No Water Supply":       "Water Distribution Team",
    "Drainage Blocked":      "Drainage Clearance Team",
    "Flooding":              "Flood Response Team",
    # Sanitation
    "Garbage":               "Waste Collection Team",
    "Garbage Dump":          "Waste Clearance Team",
    "Dead Animal":           "Animal Disposal Team",
    "Open Defecation":       "Sanitation Enforcement Team",
    # Electrical & Lighting
    "Street Light":          "Street Lighting Team",
    "Electrical Hazard":     "Emergency Electrical Team",
    "No Electricity":        "Power Restoration Team",
    "Broken Street Light":   "Street Lighting Team",
    # Public Safety & Trees
    "Tree Fallen":           "Tree Clearance Team",
    "Tree Hazard":           "Tree Inspection Team",
    "Park Maintenance":      "Parks Upkeep Team",
    # Traffic
    "Traffic Signal":        "Signal Maintenance Team",
    "Illegal Parking":       "Traffic Enforcement Team",
    "Broken Traffic Sign":   "Traffic Infrastructure Team",
    # Public Safety
    "Public Safety":         "Safety Response Team",
    "Stray Animals":         "Animal Control Team",
    "Fire Hazard":           "Fire Safety Team",
    # Construction & Property
    "Illegal Construction":  "Enforcement & Survey Team",
    "Encroachment":          "Enforcement & Survey Team",
    # Noise & Environment
    "Noise Pollution":       "Environmental Monitoring Team",
    "Air Pollution":         "Environmental Monitoring Team",
}

DEFAULT_TEAM: Final[str] = "General Field Team"

# =============================================================================
# ZONE MAPPINGS
#
# Geographic zones represent administrative divisions of the city.
# The routing engine maps complaint categories to the zone most commonly
# associated with that type of infrastructure.
#
# In a production deployment this table would be enriched with a
# location → zone lookup; for this deterministic module, the zone is
# derived from the category alone when no precise location is resolvable.
# =============================================================================

CATEGORY_TO_ZONE: Final[dict[str, str]] = {
    # Road & Infrastructure
    "Road Damage":           "Zone A",
    "Open Manhole":          "Zone A",
    "Footpath Damage":       "Zone A",
    "Road Waterlogging":     "Zone B",
    # Water & Drainage
    "Water Leakage":         "Zone B",
    "No Water Supply":       "Zone B",
    "Drainage Blocked":      "Zone B",
    "Flooding":              "Zone C",
    # Sanitation
    "Garbage":               "Zone C",
    "Garbage Dump":          "Zone C",
    "Dead Animal":           "Zone C",
    "Open Defecation":       "Zone C",
    # Electrical & Lighting
    "Street Light":          "Zone D",
    "Electrical Hazard":     "Zone D",
    "No Electricity":        "Zone D",
    "Broken Street Light":   "Zone D",
    # Public Safety & Trees
    "Tree Fallen":           "Zone A",
    "Tree Hazard":           "Zone A",
    "Park Maintenance":      "Zone A",
    # Traffic
    "Traffic Signal":        "Zone E",
    "Illegal Parking":       "Zone E",
    "Broken Traffic Sign":   "Zone E",
    # Public Safety
    "Public Safety":         "Zone F",
    "Stray Animals":         "Zone F",
    "Fire Hazard":           "Zone F",
    # Construction & Property
    "Illegal Construction":  "Zone G",
    "Encroachment":          "Zone G",
    # Noise & Environment
    "Noise Pollution":       "Zone H",
    "Air Pollution":         "Zone H",
}

DEFAULT_ZONE: Final[str] = "Zone G"

# =============================================================================
# BASE SLA MAPPINGS (hours)
#
# The base SLA is the maximum hours allowed to resolve this complaint
# type under normal (non-escalated) conditions.
#
# These values represent the standard SLA commitments for each civic
# complaint category, independent of priority level. Priority-based SLA
# overrides (when a complaint is Critical or escalated) are defined
# separately in config.py.
# =============================================================================

CATEGORY_TO_BASE_SLA: Final[dict[str, int]] = {
    # Life-threatening / immediate safety hazard → 6 hours
    "Open Manhole":          6,
    "Electrical Hazard":     6,
    "Fire Hazard":           6,
    "Flooding":              6,
    "Tree Fallen":           6,
    # High civic impact → 12 hours
    "Road Damage":           12,
    "Water Leakage":         12,
    "No Water Supply":       12,
    "No Electricity":        12,
    "Public Safety":         12,
    "Stray Animals":         12,
    # Moderate impact → 24 hours
    "Drainage Blocked":      24,
    "Road Waterlogging":     24,
    "Traffic Signal":        24,
    "Street Light":          24,
    "Broken Street Light":   24,
    "Tree Hazard":           24,
    # Lower urgency → 48 hours
    "Garbage":               48,
    "Garbage Dump":          48,
    "Footpath Damage":       48,
    "Illegal Parking":       48,
    "Broken Traffic Sign":   48,
    "Dead Animal":           48,
    "Open Defecation":       48,
    # Enforcement / administrative → 72 hours
    "Illegal Construction":  72,
    "Encroachment":          72,
    "Park Maintenance":      72,
    "Noise Pollution":       72,
    "Air Pollution":         72,
}

DEFAULT_BASE_SLA_HOURS: Final[int] = 72

# =============================================================================
# ESCALATION TRIGGER LEVELS
#
# Complaints whose priority_level falls in this set automatically trigger
# escalation regardless of other factors.
# =============================================================================

ESCALATION_PRIORITY_LEVELS: Final[frozenset[str]] = frozenset(
    {"Critical", "High"}
)

# =============================================================================
# ESCALATION TRIGGER CATEGORIES
#
# Certain categories always escalate due to public-safety severity,
# even when the LLM assigns them a lower priority level.
# =============================================================================

ALWAYS_ESCALATE_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "Electrical Hazard",
        "Open Manhole",
        "Flooding",
        "Fire Hazard",
        "Public Safety",
    }
)

# =============================================================================
# ESCALATION CLUSTER THRESHOLD
#
# If cluster_size reaches or exceeds this number, the complaint is
# escalated regardless of priority level — high community impact signals
# that the issue cannot wait for standard processing.
# =============================================================================

ESCALATION_CLUSTER_THRESHOLD: Final[int] = 10
