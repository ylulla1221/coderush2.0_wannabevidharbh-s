"""
Unit tests for the CivicFlow AI Priority Engine.

All expected values are calculated from the actual scoring model:

    Score = urgency_score + category_score + community_impact + confidence_score + sla_risk

Thresholds (config.py defaults):
    Critical ≥ 90  |  High ≥ 70  |  Medium ≥ 40  |  Low < 40

Urgency scores (constants.py):
    Critical=35  High=25  Medium=15  Low=5

Category scores (constants.py):
    Public Safety=25  Road Damage=20  (unknown → default=10)

Community impact (scoring.py):
    cluster≤1 → 0  cluster≤3 → 5  cluster≤5 → 10  cluster≤10 → 15  else → 20

Confidence scores (config.py thresholds 0.95/0.90/0.80):
    ≥0.95 → 10  ≥0.90 → 8  ≥0.80 → 6  else → 4

SLA risk (complaint_age_hours=0 in all cases below):
    age=0 → 0
"""

from __future__ import annotations

import pytest

from app.ai.priority.constants import (
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
)
from app.ai.priority.models import PriorityInput
from app.ai.priority.priority_engine import calculate_priority
from app.ai.priority.scoring import calculate_score

# ---------------------------------------------------------------------------
# Breakdown key names produced by the real scoring.py
# ---------------------------------------------------------------------------
BREAKDOWN_KEYS = {"urgency", "category", "community_impact", "confidence", "sla_risk"}


# ===========================================================================
# calculate_score() — unit tests
# ===========================================================================


def test_calculate_score_critical() -> None:
    """
    Critical urgency + Public Safety + cluster 4 + confidence 0.9 + age 0.

    Expected:
        urgency          = 35 (Critical)
        category         = 25 (Public Safety)
        community_impact = 10 (cluster 4 → ≤5 bracket)
        confidence       = 8  (0.9 ≥ 0.90 → MEDIUM bucket)
        sla_risk         = 0  (age 0)
        total            = 78  → High (70 ≤ 78 < 90)
    """
    data = PriorityInput(
        urgency="Critical",
        category="Public Safety",
        confidence=0.9,
        is_duplicate=True,
        cluster_size=4,
        complaint_age_hours=0,
    )

    score, level, breakdown, reasons = calculate_score(data)

    assert score == 78.0, f"Expected 78.0, got {score}"
    assert level == PRIORITY_HIGH, f"Expected High (78<90), got {level}"
    assert set(breakdown.keys()) == BREAKDOWN_KEYS
    assert breakdown["urgency"] == 35.0
    assert breakdown["category"] == 25.0
    assert breakdown["community_impact"] == 10.0
    assert breakdown["confidence"] == 8.0
    assert breakdown["sla_risk"] == 0.0
    assert len(reasons) > 0


def test_calculate_score_critical_reaches_critical_threshold() -> None:
    """
    Drive the score above 90 to confirm Critical level is reachable.

    Critical urgency + Electrical Hazard + cluster 11+ + high confidence + old age.

    Expected:
        urgency          = 35
        category         = 25  (Electrical Hazard)
        community_impact = 20  (cluster 15 → > 10)
        confidence       = 10  (0.97 ≥ 0.95)
        sla_risk         = 10  (age 72 ≥ SLA_CRITICAL_HOURS 48)
        total            = 100 → Critical
    """
    data = PriorityInput(
        urgency="Critical",
        category="Electrical Hazard",
        confidence=0.97,
        is_duplicate=True,
        cluster_size=15,
        complaint_age_hours=72,
    )

    score, level, breakdown, reasons = calculate_score(data)

    assert score == 100.0
    assert level == PRIORITY_CRITICAL
    assert breakdown["urgency"] == 35.0
    assert breakdown["community_impact"] == 20.0
    assert breakdown["sla_risk"] == 10.0


def test_calculate_score_low() -> None:
    """
    Low urgency + unknown category + single complaint + confidence 0.8 + age 0.

    Expected:
        urgency          = 5   (Low)
        category         = 10  (unknown → default)
        community_impact = 0   (cluster 1)
        confidence       = 6   (0.8 = LOW threshold boundary)
        sla_risk         = 0
        total            = 21  → Low (21 < 40)
    """
    data = PriorityInput(
        urgency="Low",
        category="Unknown",
        confidence=0.8,
        is_duplicate=False,
        cluster_size=1,
        complaint_age_hours=0,
    )

    score, level, breakdown, reasons = calculate_score(data)

    assert score == 21.0, f"Expected 21.0, got {score}"
    assert level == PRIORITY_LOW
    assert breakdown["urgency"] == 5.0
    assert breakdown["category"] == 10.0
    assert breakdown["community_impact"] == 0.0
    assert breakdown["confidence"] == 6.0
    assert breakdown["sla_risk"] == 0.0


def test_calculate_score_medium() -> None:
    """
    Medium urgency + Garbage + single complaint + confidence 0.9 + age 0.

    Expected:
        urgency          = 15
        category         = 8   (Garbage)
        community_impact = 0
        confidence       = 8   (0.9 ≥ 0.90)
        sla_risk         = 0
        total            = 31  → Low? 31 < 40 → Low

    Demonstrates that 'Medium' urgency alone does not guarantee Medium level.
    """
    data = PriorityInput(
        urgency="Medium",
        category="Garbage",
        confidence=0.9,
        is_duplicate=False,
        cluster_size=1,
        complaint_age_hours=0,
    )

    score, level, breakdown, reasons = calculate_score(data)

    assert score == 31.0
    assert level == PRIORITY_LOW  # 31 < MEDIUM_THRESHOLD (40)
    assert breakdown["urgency"] == 15.0


def test_calculate_score_community_impact_brackets() -> None:
    """Verify each cluster-size bracket maps to the correct community score."""
    brackets = [
        (1,  0.0),
        (2,  5.0),
        (3,  5.0),
        (4,  10.0),
        (5,  10.0),
        (6,  15.0),
        (10, 15.0),
        (11, 20.0),
    ]
    for size, expected_impact in brackets:
        data = PriorityInput(
            urgency="Low",
            category="Garbage",
            confidence=0.8,
            cluster_size=size,
            complaint_age_hours=0,
        )
        _, _, breakdown, _ = calculate_score(data)
        assert breakdown["community_impact"] == expected_impact, (
            f"cluster_size={size}: expected community_impact={expected_impact}, "
            f"got {breakdown['community_impact']}"
        )


def test_calculate_score_sla_risk_brackets() -> None:
    """Verify SLA risk score increases with complaint age."""
    # age=0 → 0; age=1 → 2; age=12 → 5; age=24 → 8; age=48 → 10
    cases = [(0, 0.0), (1, 2.0), (12, 5.0), (24, 8.0), (48, 10.0), (100, 10.0)]
    for age, expected_sla in cases:
        data = PriorityInput(
            urgency="Low",
            category="Garbage",
            confidence=0.8,
            cluster_size=1,
            complaint_age_hours=age,
        )
        _, _, breakdown, _ = calculate_score(data)
        assert breakdown["sla_risk"] == expected_sla, (
            f"age={age}h: expected sla_risk={expected_sla}, "
            f"got {breakdown['sla_risk']}"
        )


def test_calculate_score_none_urgency_uses_default() -> None:
    """None urgency falls back to DEFAULT_URGENCY_SCORE (15.0)."""
    data = PriorityInput(
        urgency=None,
        category=None,
        confidence=0.8,
        cluster_size=1,
        complaint_age_hours=0,
    )
    _, _, breakdown, _ = calculate_score(data)
    assert breakdown["urgency"] == 15.0   # DEFAULT_URGENCY_SCORE


def test_calculate_score_breakdown_keys_always_present() -> None:
    """breakdown dict must always contain all five component keys."""
    data = PriorityInput(urgency="High", category="Road Damage", confidence=0.95)
    _, _, breakdown, _ = calculate_score(data)
    assert set(breakdown.keys()) == BREAKDOWN_KEYS


# ===========================================================================
# calculate_priority() — orchestrator integration tests
# ===========================================================================


def test_priority_engine_integration_high() -> None:
    """
    High urgency + Road Damage + cluster 3 + confidence 0.95 + age 0.

    Expected:
        urgency          = 25
        category         = 20
        community_impact = 5   (cluster 3 → ≤3)
        confidence       = 10  (0.95 = HIGH threshold)
        sla_risk         = 0
        total            = 60  → Medium (40 ≤ 60 < 70)
    """
    complaint_data = {
        "urgency": "High",
        "category": "Road Damage",
        "confidence": 0.95,
    }
    duplicate_data = {
        "is_duplicate": True,
        "cluster_size": 3,
    }

    result = calculate_priority(complaint_data, duplicate_data)

    assert "priority_score" in result
    assert "priority_level" in result
    assert "breakdown" in result
    assert result["priority_score"] == 60.0
    assert result["priority_level"] == PRIORITY_MEDIUM


def test_priority_engine_integration_reaches_high() -> None:
    """
    High urgency + Flooding + cluster 6 + confidence 0.95 + age 0.

    Expected:
        urgency          = 25
        category         = 24  (Flooding)
        community_impact = 15  (cluster 6 → ≤10)
        confidence       = 10
        sla_risk         = 0
        total            = 74  → High (70 ≤ 74 < 90)
    """
    result = calculate_priority(
        complaint_data={"urgency": "High", "category": "Flooding", "confidence": 0.95},
        duplicate_data={"is_duplicate": True, "cluster_size": 6},
    )
    assert result["priority_score"] == 74.0
    assert result["priority_level"] == PRIORITY_HIGH


def test_priority_engine_result_shape() -> None:
    """Result must always contain the four required top-level keys."""
    result = calculate_priority(
        complaint_data={"urgency": "Medium", "category": "Garbage", "confidence": 0.85},
        duplicate_data={"is_duplicate": False, "cluster_size": 1},
    )
    for key in ("priority_score", "priority_level", "breakdown", "reasons"):
        assert key in result, f"Missing key: {key}"
    assert isinstance(result["priority_score"], float)
    assert isinstance(result["reasons"], list)


def test_priority_engine_invalid_input_returns_fallback() -> None:
    """priority_score > 1.0 as confidence triggers Pydantic → safe fallback."""
    result = calculate_priority(
        complaint_data={"urgency": "High", "confidence": 5.0},
        duplicate_data={},
    )
    # Fallback must still return a structurally valid result
    assert result["priority_level"] == "Medium"
    assert result["priority_score"] == 40.0


def test_priority_engine_missing_fields_use_defaults() -> None:
    """Empty dicts must not raise — all fields have safe defaults."""
    result = calculate_priority(complaint_data={}, duplicate_data={})
    assert "priority_level" in result
    assert 0.0 <= result["priority_score"] <= 100.0
